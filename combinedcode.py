import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import os
import tempfile
import io
import xlsxwriter
from fpdf import FPDF

# Define the parameter descriptions
parameter_descriptions = {
    'A1': "School_ID, Grade, student_no: Uses School_ID, Grade, and student_no to generate the ID.",
    'A2': "Block_ID, School_ID, Grade, student_no: Uses Block_ID, School_ID, Grade, and student_no to generate the ID.",
    'A3': "District_ID, School_ID, Grade, student_no: Uses District_ID, School_ID, Grade, and student_no to generate the ID.",
    'A4': "Partner_ID, School_ID, Grade, student_no: Uses Partner_ID, School_ID, Grade, and student_no to generate the ID.",
    'A5': "District_ID, Block_ID, School_ID, Grade, student_no: Uses District_ID, Block_ID, School_ID, Grade, and student_no to generate the ID.",
    'A6': "Partner_ID, Block_ID, School_ID, Grade, student_no: Uses Partner_ID, Block_ID, School_ID, Grade, and student_no to generate the ID.",
    'A7': "Partner_ID, District_ID, School_ID, Grade, student_no: Uses Partner_ID, District_ID, School_ID, Grade, and student_no to generate the ID.",
    'A8': "Partner_ID, District_ID, Block_ID, School_ID, Grade, student_no: Uses Partner_ID, District_ID, Block_ID, School_ID, Grade, and student_no to generate the ID."
}
# Define the new mapping for parameter sets
parameter_mapping = {
    'A1': "School_ID,Grade,student_no",
    'A2': "Block_ID,School_ID,Grade,student_no",
    'A3': "District_ID,School_ID,Grade,student_no",
    'A4': "Partner_ID,School_ID,Grade,student_no",
    'A5': "District_ID,Block_ID,School_ID,Grade,student_no",
    'A6': "Partner_ID,Block_ID,School_ID,Grade,student_no",
    'A7': "Partner_ID,District_ID,School_ID,Grade,student_no",
    'A8': "Partner_ID,District_ID,Block_ID,School_ID,Grade,student_no"
}
def generate_custom_id(row, params):
    params_split = params.split(',')
    custom_id = []
    for param in params_split:
        if param in row and pd.notna(row[param]):
            value = row[param]
            if isinstance(value, float) and value % 1 == 0:
                value = int(value)
            custom_id.append(str(value))
    return ''.join(custom_id)

def process_data(uploaded_file, partner_id, buffer_percent, grade, district_digits, block_digits, school_digits, student_digits, selected_param):
    data = pd.read_excel(uploaded_file)
    # Assign the Partner_ID directly
    data['Partner_ID'] = str(partner_id).zfill(len(str(partner_id)))  # Padding Partner_ID
    data['Grade'] = grade
    # Assign unique IDs for District, Block, and School, default to "00" for missing values
    data['District_ID'] = data['District'].apply(lambda x: str(data['District'].unique().tolist().index(x) + 1).zfill(district_digits) if x != "NA" else "0".zfill(district_digits))
    data['Block_ID'] = data['Block'].apply(lambda x: str(data['Block'].unique().tolist().index(x) + 1).zfill(block_digits) if x != "NA" else "0".zfill(block_digits))
    data['School_ID'] = data['School_ID'].apply(lambda x: str(data['School_ID'].unique().tolist().index(x) + 1).zfill(school_digits) if x != "NA" else "0".zfill(school_digits))
    # Calculate Total Students With Buffer based on the provided buffer percentage
    data['Total_Students_With_Buffer'] = np.floor(data['Total_Students'] * (1 + buffer_percent / 100))
    # Generate student IDs based on the calculated Total Students With Buffer

    def generate_student_ids(row):
        if pd.notna(row['Total_Students_With_Buffer']) and row['Total_Students_With_Buffer'] > 0:
            student_ids = [
                f"{row['School_ID']}{str(int(row['Grade'])).zfill(2)}{str(i).zfill(student_digits)}"
                for i in range(1, int(row['Total_Students_With_Buffer']) + 1)
            ]
            return student_ids
        return []
    data['Student_IDs'] = data.apply(generate_student_ids, axis=1)

    # Expand the data frame to have one row per student ID
    data_expanded = data.explode('Student_IDs')

    # Extract student number from the ID
    data_expanded['student_no'] = data_expanded['Student_IDs'].str[-student_digits:]

    # Use the selected parameter set for generating Custom_ID
    data_expanded['Custom_ID'] = data_expanded.apply(lambda row: generate_custom_id(row, parameter_mapping[selected_param]), axis=1)

    # Generate the additional Excel sheets with mapped columns
    data_mapped = data_expanded[['Custom_ID', 'Grade', 'School', 'School_ID', 'District', 'Block']].copy()
    data_mapped.columns = ['Roll_Number', 'Grade', 'School Name', 'School Code', 'District Name', 'Block Name']
    data_mapped['Gender'] = np.random.choice(['Male', 'Female'], size=len(data_mapped), replace=True)

    # Generate Teacher_Codes sheet
    teacher_codes = data[['School', 'School_ID']].copy()
    teacher_codes.columns = ['School Name', 'Teacher Code']
    return data_expanded, data_mapped, teacher_codes

# Function to create the attendance list PDF
def create_attendance_pdf(pdf, column_widths, column_names, image_path, info_values, df):
    pdf.add_page()

    # Page width and margins
    page_width = 210  # A4 page width in mm
    margin_left = 10
    margin_right = 10
    available_width = page_width - margin_left - margin_right

    # Calculate total column width
    total_column_width = sum(column_widths[col] for col in column_names)

    # Scale column widths if necessary
    if total_column_width > available_width:
        scaling_factor = available_width / total_column_width
        column_widths = {col: width * scaling_factor for col, width in column_widths.items()}

    # Add the combined title and subtitle in a single merged cell
    pdf.set_font('Arial', 'B', 16)
    merged_cell_width = sum(column_widths[col] for col in column_names)  # Total width based on scaled column widths
    pdf.cell(merged_cell_width, 10, 'ATTENDANCE LIST', border='LTR', align='C', ln=1)
    pdf.set_font('Arial', '', 7)
    pdf.cell(merged_cell_width, 10, '(PLEASE FILL ALL THE DETAILS IN BLOCK LETTERS)', border='LBR', align='C', ln=1)

    # Add the image in the top-right corner of the bordered cell
    pdf.image(image_path, x=pdf.get_x() + merged_cell_width - 30, y=pdf.get_y() - 18, w=28, h=12)  # Adjust position and size as needed

    # Add the additional information cell below the "ATTENDANCE LIST" cell
    pdf.set_font('Arial', 'B', 6)
    info_cell_width = merged_cell_width  # Width same as the merged title cell
    info_cell_height = 30  # Adjust height as needed
    pdf.cell(info_cell_width, info_cell_height, '', border='LBR', ln=1)
    pdf.set_xy(pdf.get_x(), pdf.get_y() - info_cell_height)  # Move back to the top of the cell

    # Add labels and fill values from the dictionary
    info_labels = {
        'PROJECT': '',
        'DISTRICT': '',
        'BLOCK': '',
        'SCHOOL NAME': '',
        'CLASS': '',
        'SECTION': ''
    }

    for label in info_labels.keys():
        for key, value in info_values.items():
            if label[:5].lower() == key[:5].lower():  # Match first 5 characters, ignoring case
                info_labels[label] = value
                break

    pdf.cell(info_cell_width, 5, f"PROJECT : {info_labels['PROJECT']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"DISTRICT : {info_labels['DISTRICT']}                                                                                                                                                                                 DATE OF ASSESSMENT : ____________________", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"BLOCK : {info_labels['BLOCK']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"SCHOOL NAME : {info_labels['SCHOOL NAME']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"CLASS : {info_labels['CLASS']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"SECTION : {info_labels['SECTION']}", border='LR', ln=1)

    # Draw a border around the table header
    pdf.set_font('Arial', 'B', 5.5)
    table_cell_height = 10

    # Table Header
    for col_name in column_names:
        pdf.cell(column_widths[col_name], table_cell_height, col_name, border=1, align='C')
    pdf.ln(table_cell_height)

    # Table Rows (based on student_count)
    pdf.set_font('Arial', '', 7)
    student_count = info_values.get('student_count', 0)  # Use 0 if 'student_count' is missing or not found

    # Fill in the student IDs for the selected school code
    student_ids = df[df['School Code'] == info_values.get('School Code', '')]['STUDENT ID'].tolist()

    for i in range(student_count):
        # Fill in S.NO column
        pdf.cell(column_widths['S.NO'], table_cell_height, str(i + 1), border=1, align='C')

        # Fill in STUDENT ID column
        student_id = student_ids[i]
        pdf.cell(column_widths['STUDENT ID'], table_cell_height, str(student_id), border=1, align='C')

        # Fill in remaining columns with empty values
        for col_name in column_names[2:]:  # Skip first two columns
            pdf.cell(column_widths[col_name], table_cell_height, '', border=1, align='C')

        pdf.ln(table_cell_height)

def main():
    st.title("Student ID Generator")
    # Initialize session state for buttons
    if 'buttons_initialized' not in st.session_state:
        st.session_state['buttons_initialized'] = True
        st.session_state['download_data'] = None
        st.session_state['download_mapped'] = None
        st.session_state['download_teachers'] = None
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
    if uploaded_file is not None:
        st.write("File uploaded successfully!")
        partner_id = st.number_input("Partner ID", min_value=0, value=0)
        buffer_percent = st.number_input("Buffer (%)", min_value=0.0, max_value=100.0, value=30.0)
        grade = st.number_input("Grade", min_value=1, value=1)
        district_digits = st.number_input("District ID Digits", min_value=1, value=2)
        block_digits = st.number_input("Block ID Digits", min_value=1, value=2)
        school_digits = st.number_input("School ID Digits", min_value=1, value=3)
        student_digits = st.number_input("Student ID Digits", min_value=1, value=4)
         # Set the title of the app
        st.title("Parameter Set")
       # URL of the image in your GitHub repository
        image_url = "https://raw.githubusercontent.com/pranay-raj-goud/Test2/main/Image.png"
       # Display the image with a caption
        st.image(image_url, caption="Select below parameters", use_column_width=True)
        selected_param = st.selectbox("Select Parameter Set", list(parameter_mapping.keys()))
        st.write(parameter_descriptions[selected_param])
        if st.button("Generate IDs"):
            data_expanded, data_mapped, teacher_codes = process_data(uploaded_file, partner_id, buffer_percent, grade, district_digits, block_digits, school_digits, student_digits, selected_param)
            # Save the data for download
            towrite1 = io.BytesIO()
            towrite2 = io.BytesIO()
            towrite3 = io.BytesIO()
            with pd.ExcelWriter(towrite1, engine='xlsxwriter') as writer:
                data_expanded.to_excel(writer, index=False)
            with pd.ExcelWriter(towrite2, engine='xlsxwriter') as writer:
                data_mapped.to_excel(writer, index=False)
            with pd.ExcelWriter(towrite3, engine='xlsxwriter') as writer:
                teacher_codes.to_excel(writer, index=False)
            towrite1.seek(0)
            towrite2.seek(0)
            towrite3.seek(0)
            # Update session state for download links
            st.session_state['download_data'] = towrite1
            st.session_state['download_mapped'] = towrite2
            st.session_state['download_teachers'] = towrite3
    # Always show download buttons
    #if st.session_state['download_data'] is not None:
        #st.download_button(label="Download Student IDs Excel", data=st.session_state['download_data'], file_name="Student_Ids.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if st.session_state['download_mapped'] is not None:
        st.download_button(label="Download Mapped Student IDs Excel", data=st.session_state['download_mapped'], file_name="Student_Ids_Mapped.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if st.session_state['download_teachers'] is not None:
        st.download_button(label="Download Teacher Codes Excel", data=st.session_state['download_teachers'], file_name="Teacher_Codes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Part 2: Attendance PDF Generation
    if st.session_state['download_mapped'] is not None:
        st.title("Attendance List PDF Generator")

        image_path = "https://raw.githubusercontent.com/AniketParasher/pdfcreator/main/cg.png"

        # Process the `data_mapped` as the Excel file for attendance list generation
        excel_data = st.session_state['download_mapped'].getvalue()

        df1 = pd.read_excel(excel_data)

        # Define possible variations of 'Student ID' column names
        student_id_variations = ['STUDENT ID', 'STUDENT_ID', 'ROLL_NUMBER', 'Roll_Number', 'Roll Number']

        # Identify the actual column name from the variations
        student_id_column = None
        for variation in student_id_variations:
            if variation in df1.columns:
                student_id_column = variation
                break

        if student_id_column is None:
            raise ValueError("No recognized student ID column found in the data")

        # Standardize column name to 'STUDENT_ID'
        df = df1.rename(columns={student_id_column: 'STUDENT ID'})

        # Process data
        grouping_columns = [col for col in df.columns if col not in ['STUDENT ID', 'Gender'] and df[col].notna().any()]
        grouped = df.groupby(grouping_columns).agg(student_count=('STUDENT ID', 'nunique')).reset_index()

        if 'CLASS' in grouped.columns and grouped['CLASS'].astype(str).str.contains('\D').any():
            grouped['CLASS'] = grouped['CLASS'].astype(str).str.extract('(\d+)')

        result = grouped.to_dict(orient='records')

        # Number of columns and column names for the table
        column_names = ['S.NO', 'STUDENT ID', 'PASSCODE', 'STUDENT NAME', 'GENDER', 'TAB ID', 'SUBJECT 1 (PRESENT/ABSENT)', 'SUBJECT 2 (PRESENT/ABSENT)']
        column_widths = {
            'S.NO': 8,
            'STUDENT ID': 18,
            'PASSCODE': 18,
            'STUDENT NAME': 61,
            'GENDER': 15,
            'TAB ID': 15,
            'SUBJECT 1 (PRESENT/ABSENT)': 35,
            'SUBJECT 2 (PRESENT/ABSENT)': 35
        }

        if st.button("Click to Generate PDFs and Zip"):
            # Create a temporary directory to save PDFs
            with tempfile.TemporaryDirectory() as tmp_dir:
                pdf_paths = []

                for record in result:
                    school_code = record.get('School Code', 'default_code')

                    # Create a PDF for each school
                    pdf = FPDF(orientation='P', unit='mm', format='A4')
                    pdf.set_left_margin(10)
                    pdf.set_right_margin(10)

                    create_attendance_pdf(pdf, column_widths, column_names, image_path, record, df)

                    # Save the PDF in the temporary directory
                    pdf_path = os.path.join(tmp_dir, f'attendance_list_{school_code}.pdf')
                    pdf.output(pdf_path)
                    pdf_paths.append(pdf_path)

                # Create a zip file containing all PDFs
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    for pdf_path in pdf_paths:
                        zip_file.write(pdf_path, os.path.basename(pdf_path))

                # Provide download link for the zip file
                st.download_button(
                    label="Click to Download Zip File",
                    data=zip_buffer.getvalue(),
                    file_name="attendance_Sheets.zip",
                    mime="application/zip"
                )

if __name__ == "__main__":
    main()
