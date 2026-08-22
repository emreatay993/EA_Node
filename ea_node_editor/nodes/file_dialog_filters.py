from __future__ import annotations

from ea_node_editor.common.scene_protocol import CAD_SCENE_SUFFIXES, FE_SCENE_SUFFIXES

ALL_FILES_FILTER = "All Files (*)"
TEXT_FILES_FILTER = (
    "Text/Data Files (*.txt *.md *.csv *.json *.jsonl *.yaml *.yml *.log);;"
    f"{ALL_FILES_FILTER}"
)
SPREADSHEET_FILES_FILTER = f"Spreadsheet Files (*.csv *.xlsx *.xlsm);;{ALL_FILES_FILTER}"
TABULAR_DATA_FILES_FILTER = (
    "Tabular Data (*.csv *.tsv *.txt *.xlsx *.xlsm *.parquet *.h5 *.hdf *.hdf5 *.npy *.npz);;"
    f"{ALL_FILES_FILTER}"
)
TABULAR_TABLE_OUTPUT_FILES_FILTER = (
    "Table Output (*.csv *.tsv *.txt *.jsonl *.xlsx *.xlsm);;"
    f"{ALL_FILES_FILTER}"
)
TABULAR_ARRAY_OUTPUT_FILES_FILTER = (
    "Array Output (*.csv *.tsv *.txt *.xlsx *.xlsm *.npy);;"
    f"{ALL_FILES_FILTER}"
)
IMAGE_FILES_FILTER = (
    "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg *.tif *.tiff);;"
    f"{ALL_FILES_FILTER}"
)
PDF_FILES_FILTER = f"PDF Files (*.pdf);;{ALL_FILES_FILTER}"
VIDEO_FILES_FILTER = (
    "Video Files (*.mp4 *.m4v *.mov *.avi *.mkv *.webm *.wmv);;"
    f"{ALL_FILES_FILTER}"
)
MAIL_FILE_SUFFIXES = (".eml", ".msg", ".oft")
MAIL_FILES_FILTER = f"Mail Files (*{' *'.join(MAIL_FILE_SUFFIXES)});;{ALL_FILES_FILTER}"
WEB_PAGE_FILES_FILTER = "Web Page Files (*.html *.htm *.xhtml);;" f"{ALL_FILES_FILTER}"
NOTEBOOK_FILES_FILTER = f"Jupyter Notebook (*.ipynb);;{ALL_FILES_FILTER}"
SCRIPT_FILES_FILTER = (
    "Script Files (*.sh *.bash *.slurm *.pbs *.lsf *.cmd *.bat *.ps1);;"
    f"{ALL_FILES_FILTER}"
)
ANSYS_DPF_RESULT_FILES_FILTER = (
    "Ansys/DPF Result Files (*.rst *.rth *.rmg *.mode *.d3plot *.h5 *.hdf5);;"
    f"{ALL_FILES_FILTER}"
)
FE_SCENE_FILES_FILTER = (
    f"Neutral FE Files (*{' *'.join(FE_SCENE_SUFFIXES)});;{ALL_FILES_FILTER}"
)
CAD_SCENE_FILES_FILTER = (
    f"Neutral CAD Files (*{' *'.join(CAD_SCENE_SUFFIXES)});;{ALL_FILES_FILTER}"
)


__all__ = [
    "ALL_FILES_FILTER",
    "ANSYS_DPF_RESULT_FILES_FILTER",
    "CAD_SCENE_FILES_FILTER",
    "FE_SCENE_FILES_FILTER",
    "IMAGE_FILES_FILTER",
    "MAIL_FILE_SUFFIXES",
    "MAIL_FILES_FILTER",
    "NOTEBOOK_FILES_FILTER",
    "PDF_FILES_FILTER",
    "SCRIPT_FILES_FILTER",
    "SPREADSHEET_FILES_FILTER",
    "TABULAR_ARRAY_OUTPUT_FILES_FILTER",
    "TABULAR_DATA_FILES_FILTER",
    "TABULAR_TABLE_OUTPUT_FILES_FILTER",
    "TEXT_FILES_FILTER",
    "VIDEO_FILES_FILTER",
    "WEB_PAGE_FILES_FILTER",
]
