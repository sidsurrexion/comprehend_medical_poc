from flask import Flask
from flask_restful import Resource, Api
import process as hwa


app = Flask(__name__)
api = Api(app)


class ExtractMedicalResourceAndSave(Resource):
    def get(self):
        self.result = hwa.process_health_scans()
        return self.result


class CollectMedicalRecords(Resource):
    def get(self):
        self.result = hwa.collect_discovered_data()
        return self.result


api.add_resource(ExtractMedicalResourceAndSave, '/process')
api.add_resource(CollectMedicalRecords, '/collect')


if __name__ == '__main__':
    app.run(host='localhost', port='5000', debug=True)
