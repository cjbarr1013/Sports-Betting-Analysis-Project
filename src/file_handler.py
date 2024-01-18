import os
import json
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
            else:
                pass
        else:
            print(f'File type .{self.type} not supported.')

    def add_to_file(self):
        if self.type == 'json':
            pass
        elif self.type == 'csv':
            pass
        else:
            print(f'File type .{self.type} not supported.')

    def __load_json(self):
        with open(self.fp, 'r') as f:
            return json.load(f)
    
    def __write_json(self, data):
        with open(self.fp, 'w') as f:
            json.dump(data, f, indent=4)

    def __csv_to_df(self):
        return pd.read_csv(self.fp)

    def __df_to_csv(self, df: pd):
        df.to_csv(self.fp, index=False)


if __name__ == "__main__":
    pass