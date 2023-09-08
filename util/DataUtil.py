import json

class DataUtil:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DataUtil, cls).__new__(cls)
        return cls.instance
    
    def __init__(self, file):
        self.file = file

    def load(self):
        with open(self.file, 'r') as data_file:
            return json.load(data_file)
    
    def updateData(self, attrMap : dict):
        data = self.load()
        for key, value in attrMap.items():
            data[key] = value
        with open(self.file, 'w') as data_file:
            json.dump(data, data_file, indent=4)
        return data