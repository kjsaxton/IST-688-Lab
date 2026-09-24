import streamlit as st

Lab1=st.Page('Lab1.py', title='Lab1')
Lab2=st.Page('Lab2.py', title='Lab2',)
Lab3 = st.Page('Lab3.py', title='Lab3')
Lab4 = st.Page('Lab4.py', title='Lab4')
Lab4 = st.Page('Lab5.py', title='Lab5', default=True)


pg = st.navigation([Lab1, Lab2, Lab3, Lab4, L])
pg.run()
