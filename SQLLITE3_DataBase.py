import sqlite3
import pandas as pd
from datetime import datetime

class medi_data_base():
    # function for establishing the connection with database
    def get_db_connection(self):
        return sqlite3.connect('MediGrid.db')

    #fuction for saving the data with dynamic table creation.
    def save_to_db(self,full_data):

        p_info = full_data.get('patient_info', {})
        raw_name = p_info.get("patient_name") or p_info.get("Name") or "Unknown_Patient"
        patient_name = str(raw_name)
        up_patient_name = patient_name.replace(' ', '_')
        

        local_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        connection=self.get_db_connection()
        c=connection.cursor()

        patient_table=f"""
        CREATE TABLE IF NOT EXISTS Prescription (
        PATIENT_NAME text,
        MEDICATION_NAME text,
        DOSAGE text,
        FREQUENCY text,
        DURATION text,
        MAP_LINK text,
        Data_Saved DATETIME 
        )"""

        c.execute(patient_table)

        presc_list = full_data.get('Prescription_info') or full_data.get('prescription_info') or []

        for item in presc_list:

            inserting_details=f"""
            INSERT INTO Prescription (PATIENT_NAME,MEDICATION_NAME,DOSAGE,FREQUENCY,DURATION,MAP_LINK,Data_Saved)
            VALUES(?,?,?,?,?,?,?)"""

            c.execute(inserting_details,(patient_name,item.get("medications", "Not provided"),
                item.get("Dosage", "Not provided"),
                item.get("Frequency", "Not provided"),
                item.get("Duration", "Not provided"),
                item.get("Map_link", "Not provided"),
                local_time
            ))
        connection.commit()
        connection.close()
        return 'Saved_Successfully'


    # this fuction will displays the entire table
    def display_table(self):
        connection=self.get_db_connection()
        c=connection.cursor()
        try:
            data=pd.read_sql_query('SELECT * FROM Prescription ORDER BY Data_Saved DESC',connection)
            display_rows=[]
            previous_timeStamp=None
            for index,row in data.iterrows():
                current_timeStamp=row['Data_Saved']

                if previous_timeStamp is not None and current_timeStamp!= previous_timeStamp:
                    empty_row= {col: '' for col in data.columns}
                    display_rows.append(empty_row)
                
                display_rows.append(row.to_dict())
                previous_timeStamp=current_timeStamp
            
            final_display_df=pd.DataFrame(display_rows)
            return final_display_df


        finally:
            connection.close()
        

    