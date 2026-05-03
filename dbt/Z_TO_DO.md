P1:
- [?] Solve the bug on incremental key end_time

P2:
- Streamlit: Opponent Error Conversion Rate: P(Win|opponent made ≥ 1 massive throw)
- Streamlit: Ability to win when reaching a decisive advantage

- Streamlit: Opening advantage stability score
    - Forward fill when the games end too soon

- Streamlit: Endgame Collapse Detector: Focus on games reaching late/very-late phases with near-equal eval and compute loss/blunder rates there. 

- Update readme.md
    - Openings
    - Data modeling strategy

Done:
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