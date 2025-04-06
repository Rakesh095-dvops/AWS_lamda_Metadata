# AWS_lamda_Metadata

# Scenario

Create an AWS Lamda Function , it will be triggered when an image will be uploaded to S3 , it will compress size and save it S3 bucket
______

## 1.Create IAM role/Policy to support Lambda 

As we are uploading images through S3, creating new images in S3. Ensure provide atleast.

    1. AmazonS3FullAccess
    2. CloudWatchLogsFullAccess 

![alt text](steps/image.png)

## 2. Create a S3 bucket.

Since we are using one S3 for AWS lambda function,We are uploading the files into ```input_files``` and AWS Lamda will Reduce the file size using ```Pillow``` and push the files to ```archive```. 

Create the S3 bucket and create folders . 

![alt text](steps/image_s3.png)

## 3. Create and configure Lamda. 

- Create a lamdba function and configure S3 as trigger with earlier created IAM role. As we are using ```boto3``` and ```pillow``` in Lamda. 

- Here we are using ARN to configure it. 
    - I have used [Klayers git](https://github.com/keithrozario/Klayers) to add 2 layers to the Function. 
    - Based on AWS region select appropiate python supported ARN [python 3.12 ARN ](https://github.com/keithrozario/Klayers/tree/master/deployments/python3.12)

![alt text](steps/image_s3_layers.png)
![alt text](steps/image_s3_lamda.png)

- Alternate method to add ```pillow``` and ```boto 3```

    - Dependencies (Pillow):
        Pillow is not included in the standard Lambda runtime. You need to include it in your deployment package.

    - (ZIP Upload): Create a deployment package locally.
        ```
        mkdir lambda_package
        pip install Pillow -t ./lambda_package
        cp lambda_function.py ./lambda_package/
        cd lambda_package
        zip -r ../deployment_package.zip .
        cd ..
        ```
    - Follow similar steps for boto3 

## 4. Configure Lamda Function 
- Create a new Lambda function named s3_archiver.
- Choose the Python 3.x runtime.
- Paste the Python code into the Lambda code editor or upload it as a .zip file.
- Set the Handler to lambda_function.lambda_handler.
- Create a test scenario using JSON and Save a private test 
- Deploy and test the function. 

![alt text](steps/image_test_logs.png)