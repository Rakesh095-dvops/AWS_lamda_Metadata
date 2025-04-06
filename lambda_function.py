import boto3
import os
import io
import logging
from PIL import Image
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client (reuse across invocations)
s3_client = boto3.client('s3')

# Configuration
INPUT_FOLDER = 'input_files/'
ARCHIVE_FOLDER = 'archive/'
COMPRESSION_QUALITY = 85 # Target quality for JPEG compression

def lambda_handler(event, context):
    """
    Handles S3 object creation events, compresses image files using Pillow,
    uploads the compressed file to an archive folder, and deletes the original.
    """
    logger.info(f"Received event: {event}")

    for record in event['Records']:
        s3_info = record['s3']
        bucket_name = s3_info['bucket']['name']
        # Decode URL-encoded characters in the key (e.g., spaces become '+')
        object_key = unquote_plus(s3_info['object']['key'])
        base_filename = os.path.basename(object_key)
        download_path = f'/tmp/{base_filename}'
        # Use a distinct name for the compressed temp file if needed, or just use BytesIO
        # compressed_path = f'/tmp/compressed_{base_filename}' # Not strictly needed if using BytesIO directly

        try:
            logger.info(f"Processing file: s3://{bucket_name}/{object_key}")

            # --- Basic Validation ---
            if object_key.startswith(ARCHIVE_FOLDER) or object_key.endswith('/'):
                logger.info(f"Skipping event for archive folder or folder object: {object_key}")
                continue
            if not object_key.startswith(INPUT_FOLDER):
                 logger.warning(f"File {object_key} is not in the expected '{INPUT_FOLDER}' folder. Skipping.")
                 continue

            # --- Download the file ---
            logger.info(f"Downloading {object_key} to {download_path}")
            s3_client.download_file(bucket_name, object_key, download_path)
            original_size = os.path.getsize(download_path)
            logger.info(f"Original file size: {original_size} bytes")

            # --- Compress the image using Pillow ---
            logger.info(f"Attempting compression with quality {COMPRESSION_QUALITY}...")
            compressed_size = -1 # Initialize
            compressed_data = None

            try:
                with Image.open(download_path) as img:
                    in_mem_file = io.BytesIO()
                    img_format = img.format if img.format else 'JPEG' # Default to JPEG

                    save_args = {}
                    # Force saving as JPEG to apply quality setting consistently
                    # Keep original extension in the archive key for clarity though
                    target_format = 'JPEG'
                    save_args['quality'] = COMPRESSION_QUALITY
                    save_args['optimize'] = True

                    # Handle transparency for formats like PNG when converting to JPEG
                    if img.mode in ("RGBA", "P"):
                         img = img.convert("RGB")

                    logger.info(f"Saving compressed image as {target_format} with args {save_args}")
                    img.save(in_mem_file, format=target_format, **save_args)
                    compressed_size = in_mem_file.tell() # Get size from BytesIO
                    in_mem_file.seek(0)
                    compressed_data = in_mem_file # Keep the BytesIO object

                compression_ratio = (1 - (compressed_size / original_size)) * 100 if original_size > 0 else 0
                logger.info(f"Compressed file size: {compressed_size} bytes")
                logger.info(f"Compression ratio: {compression_ratio:.2f}%")

            except Exception as img_err:
                 logger.error(f"Error during image compression for {object_key}: {img_err}. Cannot proceed with archiving compressed version.")
                 # If compression fails, we do NOT want to archive anything or delete original
                 raise img_err # Re-raise the exception to stop processing this file

            # --- Upload Compressed File to Archive ---
            # Construct archive key, potentially changing extension if format changed (e.g., to .jpg)
            # For simplicity, let's keep the original filename/extension in archive
            archive_key = os.path.join(ARCHIVE_FOLDER, base_filename)
            logger.info(f"Uploading compressed data to: s3://{bucket_name}/{archive_key}")
            s3_client.put_object(Bucket=bucket_name, Key=archive_key, Body=compressed_data)

            # --- Delete the Original File --- commeneted out for safety
            # Only delete if compression and upload to archive were successful
            #logger.info(f"Deleting original file: s3://{bucket_name}/{object_key}")
            #s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            #logger.info(f"Successfully processed, compressed, archived {object_key} to {archive_key}, and deleted original.")

        except s3_client.exceptions.NoSuchKey:
            logger.error(f"File not found (NoSuchKey): s3://{bucket_name}/{object_key}. It might have been deleted before processing.")
        except Exception as e:
            logger.error(f"Error processing file s3://{bucket_name}/{object_key}: {str(e)}", exc_info=True)
            # Stop processing this specific file record on error

        finally:
            # --- Clean up temporary downloaded file ---
            if os.path.exists(download_path):
                try:
                    os.remove(download_path)
                except OSError as e:
                    logger.warning(f"Could not remove temporary file {download_path}: {e}")

    return {
        'statusCode': 200,
        'body': 'Processing finished for invocation.'
    }