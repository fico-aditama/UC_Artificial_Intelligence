import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

class ChatEvaluator:
    def __init__(self):
        if 'metrics' not in st.session_state:
            st.session_state.metrics = {
                'response_times': [],
                'token_counts': [],
                'timestamps': [],
                'total_queries': 0,
                'successful_queries': 0
            }

    def record_response_time(self, start_time: float, end_time: float) -> float:
        response_time = end_time - start_time
        st.session_state.metrics['response_times'].append(response_time)
        st.session_state.metrics['timestamps'].append(datetime.now())
        st.session_state.metrics['total_queries'] += 1
        return response_time

    def calculate_average_response_time(self) -> float:
        response_times = st.session_state.metrics['response_times']
        return sum(response_times) / len(response_times) if response_times else 0

    def get_success_rate(self) -> float:
        total = st.session_state.metrics['total_queries']
        return (st.session_state.metrics['successful_queries'] / total * 100) if total > 0 else 0

    def display_metrics(self):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Queries", st.session_state.metrics['total_queries'])
        
        with col2:
            avg_response_time = self.calculate_average_response_time()
            st.metric("Avg Response Time", f"{avg_response_time:.2f}s")
        
        with col3:
            success_rate = self.get_success_rate()
            st.metric("Success Rate", f"{success_rate:.1f}%")

        if st.session_state.metrics['response_times']:
            df = pd.DataFrame({
                'timestamp': st.session_state.metrics['timestamps'],
                'response_time': st.session_state.metrics['response_times']
            })
            
            fig = px.line(df, x='timestamp', y='response_time', 
                         title='Response Time History',
                         labels={'response_time': 'Response Time (s)', 'timestamp': 'Time'})
            st.plotly_chart(fig)
