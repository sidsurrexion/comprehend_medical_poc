1. The first part of the process is to store the files on cloud. For the POC
    we used AWS S3 to store test patient files in folders prefixed by DF_. Next
    we retrieve the files using Python's boto3 library.

    ```
    files = s3.list_all_files(settings.bucket_name, settings.prefix)
    patient_files = select_only_new_patients(collect_patients_and_respective_files(files))
    ```

    We tend to collect new patient records by scanning each folder on our AWS
    bucket and selecting only those that have not been processed so far.
