import os
import json
import csv
import pandas as pd

class FileHandler:
    def __init__(self, name: str, file_path=''):
        self.name = name
        self.type = name.split('.')[-1]
        self.file_path = file_path
        self.fp = os.path.join(file_path, name)

    def load_file(self):
        if self.type == 'json':
            return self.__load_json()
        elif self.type == 'csv':
            return self.__csv_to_df()
        else:
            print(f'File type .{self.type} not supported.')

    def write_file(self, data):
        if self.type == 'json':
            self.__write_json(data)
        elif self.type == 'csv':
            if type(data) is pd.core.frame.DataFrame:
                self.__df_to_csv(data)
            elif type(data) is list:
                self.__list_to_csv(data)        
        else:
            print(f'File type .{self.type} not supported.')

    def add_to_file(self, data):
        if self.type == 'json':
            self.__add_to_json(data)
        elif self.type == 'csv':
            self.__add_to_csv(data)
        else:
            print(f'File type .{self.type} not supported.')

    def __load_json(self):
        with open(self.fp, 'r') as f:
            return json.load(f)
    
    def __write_json(self, data):
        with open(self.fp, 'w') as f:
            json.dump(data, f, indent=4)

    def __add_to_json(self, data):
        with open(self.fp) as f:
            json_data = json.load(f)
        
        if type(json_data) is list:
            json_data.append(data)
        elif type(json_data) is dict:
            json_data.update(data)
        
        with open(self.fp, 'w') as f:
            json.dump(json_data, f, indent=4)

    def __csv_to_df(self):
        return pd.read_csv(self.fp)

    def __df_to_csv(self, df: pd):
        df.to_csv(self.fp, index=False)

    def __list_to_csv(self, data):
        with open(self.fp, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(data)

    def __add_to_csv(self, data):
        with open(self.fp, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(data)


if __name__ == "__main__":
    pass