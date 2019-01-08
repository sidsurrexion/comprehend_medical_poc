## Process Flow Document ##


1. The first part of the process is to store the files on cloud. For the POC
    we used AWS S3 to store test patient files in folders prefixed by DF_. Next
    we retrieve the files using Python's boto3 library.

    ```
    files = s3.list_all_files(settings.bucket_name, settings.prefix)
    patient_files = select_only_new_patients(collect_patients_and_respective_files(files))
    ```

    We tend to collect new patient records by scanning each folder on our AWS
    bucket and selecting only those that have not been processed so far.


2. Once the patient files are retrieved from AWS S3 each file is then processed
    for Object Character Recognition (OCR). We use Google's Cloud Vision API to
    perform OCR but it requires the input files to be in 'JPEG' format. So an
    initial file formatting is required to get the corresponding OCR text for the
    file.

    ```
    for patient in patient_files.keys():
        patient_to_text_map[patient] = {}
        mapper = patient_to_text_map[patient]
        partial_process_patient_files = partial(process_patient_files, mapper)

    def process_patient_files(file, mapper):
        mapper[file] = {}
        extension = file.split('.')[-1]
        with NamedTemporaryFile(suffix='.' + extension) as f:
            s3.download_file(settings.bucket_name, file, f.name)
            with NamedTemporaryFile(suffix='.jpg') as g:
                if extension == 'pdf':
                    create_image_file_from_pdf(f.name, g.name)
                    ocr_text = extract_handwritten_text_using_google_cloud_api(g.name)
                elif extension == 'tiff':
                    image = Image.open(f.name)
                    image.save(g.name, "JPEG", quality=100)
                    ocr_text = extract_handwritten_text_using_google_cloud_api(g.name)
                else:
                    ocr_text = extract_handwritten_text_using_google_cloud_api(f.name)
            comprehend_medical_result = s3.detect_entities(ocr_text)
            mapper[file] = metadata.prepare_metadata_catalog(comprehend_medical_result)
    ```

3. Once the initial file formatting is performed Google Cloud Vision API is used
    for text extraction.

    ```
    def extract_handwritten_text_using_google_cloud_api(file_path):
        with open(file_path, 'rb') as image_file:
            content = image_file.read()
        client = vision.ImageAnnotatorClient()
        response = client.annotate_image({
            'image': {'content': content}
        })
        converted_text = response.text_annotations[0].description
        return converted_text
    ```
