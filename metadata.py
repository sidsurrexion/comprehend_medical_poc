def get_personal_health_information():
    return {
        'AGE': [],
        'NAME': [],
        'PHONE_OR_FAX': [],
        'EMAIL': [],
        'ID': [],
        'URL': [],
        'ADDRESS': [],
        'PROFESSION': [],
        'DATE': []
    }


def get_medication_information():
    return {
        'GENERIC_NAME': '',
        'BRAND_NAME': '',
        'Attributes': [],
        'Traits': []
    }


def get_medical_condition_information():
    return {
        'DX_NAME': '',
        'ACUITY': [],
        'Traits': []
    }


def get_test_treatment_procedure_information():
    return {
        'TEST_NAME': '',
        'TREATMENT_NAME': '',
        'PROCEDURE_NAME': '',
        'Attributes': []
    }


def get_anatomy_information():
    return {
        'SYSTEM_ORGAN_SITE': '',
        'DIRECTION': []
    }


def get_overall_components():
    return {
        'PROTECTED_HEALTH_INFORMATION': [],
        'MEDICATION': [],
        'MEDICAL_CONDITION': [],
        'TEST_TREATMENT_PROCEDURE': [],
        'ANATOMY': []
    }


def get_offset(categorical_data):
    return {
        'BeginOffset': categorical_data['BeginOffset'],
        'EndOffset': categorical_data['EndOffset']
    }


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
                ongoing_category_component['Attribute'] = categorical_data['Attribute']
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


def filter_personal_health_information(components):
    protected_health_information = []
    dates = []
    for health_info in components['PROTECTED_HEALTH_INFORMATION']:
        if health_info['NAME']:
            protected_health_information.append(health_info)
        else:
            if health_info['DATE']:
                dates.extend(health_info['DATE'])
    components['PROTECTED_HEALTH_INFORMATION'] = protected_health_information
    components['DATES'] = list(set(dates))
    return components


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


def filter_initial_test_procedures(components):
    test_procedures = []
    for test_procedure in components['TEST_TREATMENT_PROCEDURE']:
        if test_procedure['Attributes'] and len(test_procedure['TEST_NAME']) > 1:
            test_procedures.append(test_procedure)
    components['TEST_TREATMENT_PROCEDURE'] = test_procedures
    return components
