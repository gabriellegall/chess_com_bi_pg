P1:
- Solve the bug on incremental key end_time

P2:
- Remove SELECT * in the int layer and beyond
- Implement SQL fluff
- Update the meta keys
- Update the Streamlit app with the new data model

Done:
- [OK] Add an index key on the raw_ tables
- [OK] Update the run_all to execute --exclude package
- [OK] Rename stg_ to raw_ for Python scripts
- [OK] Optimize incremental update on int_openings
- [OK] Check the incremental updates work as expected