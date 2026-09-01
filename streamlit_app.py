import streamlit as st

Lab1=st.Page('Lab1.py', title='Lab1')
Lab2=st.Page('Lab2.py', title='Lab2', default=True)

pg=st.navigation([Lab1,Lab2])
pg.run()
