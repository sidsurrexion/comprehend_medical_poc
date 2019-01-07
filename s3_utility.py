import boto3
import os


def list_buckets():
    buckets = boto3.client('s3').list_buckets()
    return buckets


def read_file_in_bucket(bucket_name, path):
    return boto3.client('s3').get_object(Bucket=bucket_name, Key=path)[
        'Body'].read().decode("utf-8")


def put_object(bucket_name, path, data):
    boto3.resource('s3').Bucket(bucket_name).put_object(Key=path, Body=data)


def list_all_files(bucket_name, prefix):
    contents = boto3.client('s3').list_objects_v2(Bucket=bucket_name, Prefix=prefix)['Contents']
    if not contents:
        return
    return [content['Key'] for content in contents]


def delete_object(bucket_name, path):
    boto3.client('s3').delete_object(Bucket=bucket_name, Key=path)


def detect_entities(text):
    try:
        client = boto3.client(service_name='comprehendmedical')
        return client.detect_entities(Text=text)['Entities']
    except Exception as ex:
        str(ex)
        return {}


def mass_upload(bucket_name, folder, folder_inside_bucket):
    list_folders = os.listdir(folder)
    for f in list_folders:
        if f == '.DS_Store':
            continue
        folder_path = os.path.join(folder, f)
        for file in os.listdir(folder_path):
            if file == '.DS_Store':
                continue
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                boto3.resource('s3').meta.client.upload_file(file_path, bucket_name,
                                                             folder_inside_bucket + '/' + f + '/' + file)
            else:
                for child in os.listdir(file_path):
                    if child == '.DS_Store':
                        continue
                    child_path = os.path.join(file_path, child)
                    boto3.resource('s3').meta.client.upload_file(
                        child_path, bucket_name, folder_inside_bucket + '/' + f + '/' + file + '/' + child)


def download_file(bucket_name, key, file_path):
    boto3.resource('s3').meta.client.download_file(bucket_name, key, file_path)
