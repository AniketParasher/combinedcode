import zipfile
import os
import tempfile
import io
import streamlit as st
import pandas as pd
from fpdf import FPDF

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

    pdf.cell(info_cell_width, 5, f"PROJECT: {info_labels['PROJECT']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"DISTRICT: {info_labels['DISTRICT']}                                                                                                                                                                            DATE OF ASSESSMENT : ____________________", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"BLOCK: {info_labels['BLOCK']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"SCHOOL NAME: {info_labels['SCHOOL NAME']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"CLASS: {info_labels['CLASS']}", border='LR', ln=1)
    pdf.cell(info_cell_width, 5, f"SECTION: {info_labels['SECTION']}", border='LR', ln=1)

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

# Streamlit App
def main():
    st.title("Hello! This is CGs Attendance List PDF Generator")

    # Upload Excel and Image files
    excel_file = st.file_uploader("Upload Excel file", type=["xlsx"])
    image_path = "https://raw.githubusercontent.com/AniketParasher/pdfcreator/main/cg.png"

    if excel_file and image_path:
        # Read Excel file
        df = pd.read_excel(excel_file)

        # Process data
        grouping_columns = [col for col in df.columns if col not in ['STUDENT ID'] and df[col].notna().any()]
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
