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
    for Optical Character Recognition (OCR). We use Google's Cloud Vision API to
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


4. With the extracted OCR texts, AWS Comprehend Medical API is then called to
    interpret medical information pertaining to Protected Health Information (PHI),
    medical condition, test procedure names, anatomy and medication.

    ```
    comprehend_medical_result = s3.detect_entities(ocr_text)
    mapper[file] = metadata.prepare_metadata_catalog(comprehend_medical_result)
    ```


5. Even though AWS comprehend categorizes the medical information it still needs
    editing with respect to associating PHI based upon content offsets and removing
    redundant medical conditions. For similar anatomical information, position
    of the anatomy is combined together.

    ```
    # Offset Management

    def prepare_metadata_catalog(result):
        components = get_overall_components()
        previous_category = ''
        previous_offset = get_offset(result[0])
        ongoing_category_component = {}
        for categorical_data in result:
            current_category = categorical_data['Category']

            if (previous_category and previous_category != current_category) or (
                    previous_category and previous_category == current_category and
                    categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20):
                components[previous_category].append(ongoing_category_component)

            if current_category == 'PROTECTED_HEALTH_INFORMATION':
                if current_category != previous_category:
                    ongoing_category_component = get_personal_health_information()
                else:
                    if categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20:
                        ongoing_category_component = get_personal_health_information()
                ongoing_category_component[categorical_data['Type']].append(categorical_data['Text'])

            elif current_category == 'MEDICATION':
                if current_category != previous_category:
                    ongoing_category_component = get_medication_information()
                else:
                    if categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20:
                        ongoing_category_component = get_medication_information()
                ongoing_category_component[categorical_data['Type']] = categorical_data['Text']
                if 'Attributes' in categorical_data and categorical_data['Attributes']:
                    ongoing_category_component['Attributes'] = categorical_data['Attributes']
                if 'Traits' in categorical_data and categorical_data['Traits']:
                    ongoing_category_component['Traits'] = categorical_data['Traits']

            elif current_category == 'MEDICAL_CONDITION':
                if current_category != previous_category:
                    ongoing_category_component = get_medical_condition_information()
                else:
                    if categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20:
                        ongoing_category_component = get_medical_condition_information()
                if categorical_data['Type'] == 'DX_NAME':
                    ongoing_category_component[categorical_data['Type']] = categorical_data['Text']
                else:
                    ongoing_category_component[categorical_data['Type']].append(categorical_data['Text'])

                if 'Traits' in categorical_data and categorical_data['Traits']:
                    ongoing_category_component['Traits'] = categorical_data['Traits']

            elif current_category == 'TEST_TREATMENT_PROCEDURE':
                if current_category != previous_category:
                    ongoing_category_component = get_test_treatment_procedure_information()
                else:
                    if categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20:
                        ongoing_category_component = get_test_treatment_procedure_information()
                ongoing_category_component[categorical_data['Type']] = categorical_data['Text']
                if 'Attributes' in categorical_data and categorical_data['Attributes']:
                    ongoing_category_component['Attributes'] = categorical_data['Attributes']

            else:
                if current_category != previous_category:
                    ongoing_category_component = get_anatomy_information()
                else:
                    if categorical_data['BeginOffset'] - previous_offset['EndOffset'] > 20:
                        ongoing_category_component = get_anatomy_information()
                if categorical_data['Type'] == 'SYSTEM_ORGAN_SITE':
                    ongoing_category_component[categorical_data['Type']] = categorical_data['Text']
                else:
                    ongoing_category_component[categorical_data['Type']].append(categorical_data['Text'])
            previous_category = current_category
            previous_offset = get_offset(categorical_data)
        components[previous_category].append(ongoing_category_component)
        components = filter_personal_health_information(components)
        components = filter_anatomical_data(components)
        components = filter_medical_conditions(components)
        components = filter_initial_test_procedures(components)
        return filter_personal_health_information(components)
    ```

    ```
    def filter_anatomical_data(components):
        organ_site_to_direction_map = {}
        anatomies = []
        for anatomy in components['ANATOMY']:
            if anatomy['SYSTEM_ORGAN_SITE'].lower() not in organ_site_to_direction_map:
                organ_site_to_direction_map[anatomy['SYSTEM_ORGAN_SITE'].lower()] = anatomy['DIRECTION']
            else:
                organ_site_to_direction_map[anatomy['SYSTEM_ORGAN_SITE'].lower()].extend(anatomy['DIRECTION'])
        for key, value in organ_site_to_direction_map.items():
            anatomy = get_anatomy_information()
            anatomy['SYSTEM_ORGAN_SITE'] = key
            anatomy['DIRECTION'] = list(set(value))
            anatomies.append(anatomy)
        components['ANATOMY'] = anatomies
        return components


    def filter_medical_conditions(components):
        medical_condition_list = []
        unique_dx_names = set()
        for medical_condition in components['MEDICAL_CONDITION']:
            if medical_condition['Traits'] and medical_condition['DX_NAME'].lower() not in unique_dx_names:
                for trait in medical_condition['Traits']:
                    if trait['Name'] == 'DIAGNOSIS' and trait['Score'] > 0.9:
                        medical_condition_list.append(medical_condition)
                        unique_dx_names.add(medical_condition['DX_NAME'].lower())
        components['MEDICAL_CONDITION'] = medical_condition_list
        return components
    ```

6. Lastly the information is stored in each of the patient folders that is also
    used to filter which patients have been processed.

    ```
    s3.put_object(settings.bucket_name, join(settings.prefix, *[patient,
                                                                settings.discovery_folder,
                                                                settings.discovery_file]), data)
    ```


7. An individual patient file takes around 4-5 seconds for OCR extraction and 3-4
    seconds for NLP through AWS Comprehend Medical. To speed up the process each
    patient's file is run through multiple processors as the volume in each DF_
    could be very large.

    ```
    partial_process_patient_files = partial(process_patient_files, mapper)
    with Pool() as pool:
        pool.map(partial_process_patient_files, patient_files[patient])
    ```

8. The entire process is orchestrated through Docker and a nightly batch job is
    scheduled through AWS CloudWatch that triggers AWS batch running the Docker
    container inside AWS EC2.

    ```
    job_queue_name = command_line_args.repo_name + '_job_queue'
    job_definition_name = command_line_args.repo_name + '_job_definition'
    aws_lambda_function_name = command_line_args.repo_name +\
        "_aws_lambda_function"
    deploy_settings = get_deploy_settings()
    docker_image = deploy_settings["DOCKER_IMAGE"]
    aws_account_id = boto3.client('sts').get_caller_identity().get('Account')
    schedule_expression = "cron(15 11 ? * * *)"

    create_update_aws_batch_resources(
        aws_account_id, compute_env_name, job_queue_name, job_definition_name,
        docker_image, command_line_args.shell_script_to_run_app)

    create_update_aws_lambda_function(
        aws_account_id, aws_lambda_function_name, command_line_args.repo_name)

    create_update_aws_cloudwatch_trigger(
        aws_lambda_function_name, deploy_settings, schedule_expression)

    print("Deployed Successfully")
    ```
