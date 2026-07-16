from ingestion import list_files_in_s3
try:
    files = list_files_in_s3()
    print("Files:", files)
except Exception as e:
    import traceback
    traceback.print_exc()
