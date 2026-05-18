Pre-requisite:
- Test the periodic full-refresh
- Use uv instead of Pip (inside Docker too)
- Align all versions
- Consistency in Python func naming

P1:
- Optimize the Streamlit app (code cleanup)
- Optimize makefile
- Update readme.md
    - Update the Mermaid graph
    - Update the PNG images
    - Review the consistency (e.g. ``) and quality of the readme

Done:
- [OK] Test again the dockerized model
- [OK] Test the changes on [run_timestamp] field
- [OK] DRY on processable games
- [OK] Streamlit: Opening advantage stability score
    - [OK] Forward fill when the games end too soon  
- [OK] Perform Streamlit integration testing
- [OK] Review the model definitions
- [OK] Ensure the doc has Jinja placeholders
- [OK] Delete the /n in the definitions
- [OK] Spacing in Jinja config blocks in SQL
- [OK] Update the meta keys
- [OK] Update the definitions
- [OK] Update the Streamlit app with the new data model
- [OK] Capitalize SQL keywords
- [OK] Remove SELECT * in the int & fct layer
- [OK] Implement SQL fluff
- [OK] Add an index key on the raw_ tables
- [OK] Update the run_all to execute --exclude package
- [OK] Rename stg_ to raw_ for Python scripts
- [OK] Optimize incremental update on int_openings
- [OK] Check the incremental updates work as expected
