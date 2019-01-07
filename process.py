from PIL import Image
from google.cloud import vision
from tempfile import NamedTemporaryFile
from functools import partial
from multiprocessing import Pool
from pdf2image import convert_from_path
import s3_utility as s3
import settings
import metadata
import json
from os.path import join


def create_image_file_from_pdf(pdf_file_path, image_file_path):
    images = convert_from_path(pdf_file_path, 500)
    widths, heights = zip(*(i.size for i in images))
    total_width = max(widths)
    total_height = sum(heights)
    new_im = Image.new('RGB', (total_width, total_height))
    y_offset = 0
    for im in images:
        new_im.paste(im, (0, y_offset))
        y_offset += im.size[0]
    new_im.save(image_file_path)


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


def process_health_scans():
    files = s3.list_all_files(settings.bucket_name, settings.prefix)
    patient_files = select_only_new_patients(collect_patients_and_respective_files(files))
    patient_to_text_map = {}
    for patient in patient_files.keys():
        patient_to_text_map[patient] = {}
        mapper = patient_to_text_map[patient]
        partial_process_patient_files = partial(process_patient_files, mapper)
        with Pool() as pool:
            pool.map(partial_process_patient_files, patient_files[patient])
        data = json.dumps(patient_to_text_map[patient], indent=4)
        s3.put_object(settings.bucket_name, join(settings.prefix, *[patient,
                                                                    settings.discovery_folder,
                                                                    settings.discovery_file]), data)


def collect_patients_and_respective_files(files):
    patient_file_map = {}
    patients = set([file.split('/')[1] for file in files])
    for patient in patients:
        patient_file_map[patient] = [file for file in files for entity in file.split('/') if entity == patient]
    return patient_file_map


def select_only_new_patients(patient_files_map):
    selected_patients = {}
    for k, v in patient_files_map.items():
        flag = False
        for file in v:
            if 'data_discovery' in file:
                flag = True
                break
        if not flag:
            selected_patients[k] = v
    return {k: v for k, v in selected_patients.items() if k}


def extract_handwritten_text_using_google_cloud_api(file_path):
    with open(file_path, 'rb') as image_file:
        content = image_file.read()
    client = vision.ImageAnnotatorClient()
    response = client.annotate_image({
        'image': {'content': content}
    })
    converted_text = response.text_annotations[0].description
    return converted_text


if __name__ == '__main__':
    process_health_scans()
