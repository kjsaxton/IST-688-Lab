import streamlit as st

Lab1=st.Page('Lab1.py', title='Lab1')
Lab2=st.Page('Lab2.py', title='Lab2', default=True)
Lab3 = st.Page('Lab3.py', title='Lab3')

pg = st.navigation([Lab1, Lab2, Lab3])
pg.run()
