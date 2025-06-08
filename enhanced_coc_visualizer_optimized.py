import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="CoC Homeless Data Visualization | 2007-2024",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add CSS styles
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .stTitle {
        color: #1f4e79;
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .stSelectbox, .stMultiselect {
        margin-bottom: 1rem;
    }
    .chart-container {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class EnhancedCoCVisualizer:
    def __init__(self):
        self.gdf = None
        self.homeless_indicators = [
            'Overall Homeless',
            'Sheltered ES Homeless', 
            'Sheltered TH Homeless',
            'Sheltered Total Homeless',
            'Unsheltered Homeless',
            'Overall Homeless Individuals',
            'Sheltered ES Homeless Individuals',
            'Sheltered TH Homeless Individuals', 
            'Sheltered Total Homeless Individuals',
            'Unsheltered Homeless Individuals',
            'Overall Homeless People in Families',
            'Sheltered ES Homeless People in Families',
            'Sheltered TH Homeless People in Families',
            'Sheltered Total Homeless People in Families',
            'Unsheltered Homeless People in Families',
            'Overall Homeless Family Households',
            'Sheltered ES Homeless Family Households',
            'Sheltered TH Homeless Family Households',
            'Sheltered Total Homeless Family Households',
            'Unsheltered Homeless Family Households',
            'Overall Chronically Homeless Individuals',
            'Sheltered Total Chronically Homeless Individuals',
            'Unsheltered Chronically Homeless Individuals'
        ]
        
    @st.cache_data
    def load_data(_self):
        """Load GPKG geographic data"""
        try:
            gdf = gpd.read_file("Final_CoC_Time_Data_optimized.gpkg")
            
            # Data cleaning
            gdf = gdf.dropna(subset=['CoC Number', 'CoC Name', 'Year'])
            
            # Convert year to integer
            gdf['Year'] = gdf['Year'].astype(int)
            
            # Handle problematic data in numeric columns
            numeric_cols = [col for col in _self.homeless_indicators if col in gdf.columns]
            for col in numeric_cols:
                gdf[col] = pd.to_numeric(gdf[col], errors='coerce').fillna(0)
            
            # Convert coordinate system to Web Mercator for map display
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            st.success(f"✅ Successfully loaded {len(gdf)} geographic data records")
            return gdf
            
        except Exception as e:
            st.error(f"❌ Failed to load GPKG file: {str(e)}")
            return None
    
    def create_interactive_map(self, gdf_filtered, selected_indicator):
        """Create interactive map"""
        if len(gdf_filtered) == 0:
            return None
            
        # Use fixed US center point
        center_lat, center_lon = 39.8283, -98.5795
        
        # Create choropleth map
        fig = go.Figure()
        
        # Get geometric center points for scatter layer
        try:
            centroids = gdf_filtered.geometry.centroid
            lats = [point.y if hasattr(point, 'y') else 39.8283 for point in centroids]
            lons = [point.x if hasattr(point, 'x') else -98.5795 for point in centroids]
        except Exception as e:
            # If geometric data has issues, use default coordinates
            st.warning(f"Geographic data processing error, using default coordinates: {str(e)}")
            lats = [39.8283] * len(gdf_filtered)
            lons = [-98.5795] * len(gdf_filtered)
        
        # Create hover text
        hover_text = []
        for _, row in gdf_filtered.iterrows():
            text = f"<b>{row['CoC Name']}</b><br>"
            text += f"CoC Number: {row['CoC Number']}<br>"
            text += f"State: {row['State']}<br>"
            text += f"Category: {row['CoC Category']}<br>"
            text += f"Year: {row['Year']}<br>"
            text += f"Region: {row['Region']}<br>"
            text += f"Division: {row['Division']}<br>"
            text += f"<b>{selected_indicator}: {row[selected_indicator]:,.0f}</b><br>"
            text += f"Total Homeless: {row['Overall Homeless']:,.0f}<br>"
            text += f"Sheltered: {row['Sheltered Total Homeless']:,.0f}<br>"
            text += f"Unsheltered: {row['Unsheltered Homeless']:,.0f}"
            hover_text.append(text)
        
        # Calculate marker size and color
        values = gdf_filtered[selected_indicator]
        # Ensure values are numeric type, handle NaN values
        values = pd.to_numeric(values, errors='coerce').fillna(0).values
        
        # Avoid division by zero error
        max_val = max(values) if len(values) > 0 and max(values) > 0 else 1
        min_val = min(values) if len(values) > 0 else 0
        
        # Marker size (8-40 pixels)
        if max_val > min_val:
            sizes = 8 + (values - min_val) / (max_val - min_val) * 32
        else:
            sizes = np.full(len(values), 15)  # Default size
        sizes = np.clip(sizes, 8, 40)
        
        # Add scatter layer
        fig.add_trace(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=sizes,
                color=values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title=selected_indicator
                ),
                opacity=0.8
            ),
            text=hover_text,
            hovertemplate='%{text}<extra></extra>',
            name='CoC Areas'
        ))
        
        # Map layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=3.2
            ),
            height=700,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False,
            title=dict(
                text=f"{selected_indicator} Geographic Distribution",
                x=0.5,
                font=dict(size=16, color='#1f4e79')
            )
        )
        
        return fig
    
    def create_summary_metrics(self, gdf_filtered):
        """Create summary metrics cards"""
        total_cocs = len(gdf_filtered)
        total_homeless = gdf_filtered['Overall Homeless'].sum()
        total_sheltered = gdf_filtered['Sheltered Total Homeless'].sum()
        total_unsheltered = gdf_filtered['Unsheltered Homeless'].sum()
        total_individuals = gdf_filtered['Overall Homeless Individuals'].sum()
        total_families = gdf_filtered['Overall Homeless People in Families'].sum()
        total_chronic = gdf_filtered['Overall Chronically Homeless Individuals'].sum()
        
        # Calculate percentages
        sheltered_pct = (total_sheltered / total_homeless * 100) if total_homeless > 0 else 0
        unsheltered_pct = (total_unsheltered / total_homeless * 100) if total_homeless > 0 else 0
        chronic_pct = (total_chronic / total_homeless * 100) if total_homeless > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total CoC Areas",
                f"{total_cocs:,}",
                delta=None
            )
            
        with col2:
            st.metric(
                "Total Homeless",
                f"{total_homeless:,.0f}",
                delta=None
            )
            
        with col3:
            st.metric(
                "Sheltered",
                f"{total_sheltered:,.0f}",
                delta=f"{sheltered_pct:.1f}%"
            )
            
        with col4:
            st.metric(
                "Unsheltered", 
                f"{total_unsheltered:,.0f}",
                delta=f"{unsheltered_pct:.1f}%"
            )
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                "Individuals", 
                f"{total_individuals:,.0f}",
                delta=f"{total_individuals/total_homeless*100:.1f}%" if total_homeless > 0 else "0%"
            )
            
        with col6:
            st.metric(
                "People in Families",
                f"{total_families:,.0f}",
                delta=f"{total_families/total_homeless*100:.1f}%" if total_homeless > 0 else "0%"
            )
            
        with col7:
            st.metric(
                "Chronically Homeless",
                f"{total_chronic:,.0f}",
                delta=f"{chronic_pct:.1f}%"
            )
            
        with col8:
            family_households = gdf_filtered['Overall Homeless Family Households'].sum()
            st.metric(
                "Family Households",
                f"{family_households:,.0f}",
                delta=None
            )
    
    def create_trend_analysis(self, gdf, selected_states, selected_indicator):
        """Create time trend analysis"""
        if len(selected_states) == 0:
            trend_data = gdf.groupby('Year')[selected_indicator].sum().reset_index()
            title = f"US National {selected_indicator} Trend"
        else:
            trend_data = gdf[gdf['State'].isin(selected_states)].groupby('Year')[selected_indicator].sum().reset_index()
            title = f"Selected States {selected_indicator} Trend"
        
        fig = px.line(
            trend_data, 
            x='Year', 
            y=selected_indicator,
            title=title,
            markers=True
        )
        
        fig.update_layout(
            height=400,
            xaxis_title="Year",
            yaxis_title=selected_indicator,
            title_x=0.5,
            title_font_size=16
        )
        
        return fig
    
    def create_state_comparison(self, gdf_filtered, selected_indicator):
        """Create state comparison chart"""
        state_stats = gdf_filtered.groupby('State')[selected_indicator].sum().sort_values(ascending=False).head(15)
        
        fig = px.bar(
            x=state_stats.values,
            y=state_stats.index,
            orientation='h',
            title=f"Top 15 States by {selected_indicator}",
            labels={'x': selected_indicator, 'y': 'State'}
        )
        
        fig.update_layout(
            height=500,
            title_x=0.5,
            title_font_size=16
        )
        
        return fig
    
    def create_category_analysis(self, gdf_filtered, selected_indicator):
        """Create CoC category analysis"""
        category_stats = gdf_filtered.groupby('CoC Category')[selected_indicator].sum()
        
        fig = px.pie(
            values=category_stats.values,
            names=category_stats.index,
            title=f"CoC Category {selected_indicator} Distribution"
        )
        
        fig.update_layout(
            height=400,
            title_x=0.5,
            title_font_size=16
        )
        
        return fig
    
    def create_correlation_analysis(self, gdf_filtered):
        """Create indicator correlation analysis"""
        # Select key indicators for correlation analysis
        key_indicators = [
            'Overall Homeless',
            'Sheltered Total Homeless', 
            'Unsheltered Homeless',
            'Overall Homeless Individuals',
            'Overall Homeless People in Families',
            'Overall Chronically Homeless Individuals'
        ]
        
        correlation_data = gdf_filtered[key_indicators].corr()
        
        fig = px.imshow(
            correlation_data,
            title="Key Indicators Correlation Analysis",
            color_continuous_scale="RdBu_r",
            aspect="auto"
        )
        
        fig.update_layout(
            height=500,
            title_x=0.5,
            title_font_size=16
        )
        
        return fig
    
    def run(self):
        """Run main application"""
        st.title("🏠 CoC Homeless Data Visualization System")
        st.markdown("""
        <div style='text-align: center; color: #666; margin-bottom: 2rem;'>
            <p>Based on HUD CoC Data (2007-2024) | Interactive Geographic Data Visualization and Trend Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Load data
        if self.gdf is None:
            self.gdf = self.load_data()
        
        if self.gdf is None:
            st.error("❌ Unable to load data, please check if GPKG file exists")
            return
        
        # Sidebar control panel
        st.sidebar.markdown("## 📊 Data Filtering and Controls")
        
        # Year selection
        years = sorted(self.gdf['Year'].unique())
        selected_year = st.sidebar.selectbox(
            "🗓️ Select Year",
            years,
            index=len(years)-1
        )
        
        # Indicator selection
        selected_indicator = st.sidebar.selectbox(
            "📈 Select Analysis Indicator",
            self.homeless_indicators,
            index=0
        )
        
        # State selection
        states = sorted(self.gdf['State'].unique())
        selected_states = st.sidebar.multiselect(
            "🗺️ Select States (leave empty to show all)",
            states,
            default=[]
        )
        
        # CoC category selection
        categories = sorted(self.gdf['CoC Category'].dropna().unique())
        selected_categories = st.sidebar.multiselect(
            "🏘️ Select CoC Categories (leave empty to show all)",
            categories,
            default=[]
        )
        
        # Value range filtering
        if selected_indicator in self.gdf.columns:
            min_val = float(self.gdf[selected_indicator].min())
            max_val = float(self.gdf[selected_indicator].max())
            
            if max_val > min_val:
                value_range = st.sidebar.slider(
                    f"📊 {selected_indicator} Value Range",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val),
                    step=(max_val - min_val) / 100
                )
        
        # Data filtering
        gdf_filtered = self.gdf[self.gdf['Year'] == selected_year].copy()
        
        if selected_states:
            gdf_filtered = gdf_filtered[gdf_filtered['State'].isin(selected_states)]
        
        if selected_categories:
            gdf_filtered = gdf_filtered[gdf_filtered['CoC Category'].isin(selected_categories)]
        
        if selected_indicator in self.gdf.columns and 'value_range' in locals():
            gdf_filtered = gdf_filtered[
                (gdf_filtered[selected_indicator] >= value_range[0]) &
                (gdf_filtered[selected_indicator] <= value_range[1])
            ]
        
        # Main content area
        if len(gdf_filtered) == 0:
            st.warning("⚠️ No data matches the filter criteria")
            return
        
        # Display summary metrics
        st.markdown(f"### 📊 {selected_year} Data Overview")
        self.create_summary_metrics(gdf_filtered)
        
        st.markdown("---")
        
        # Create column layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Display interactive map
            st.markdown(f"### 🗺️ {selected_indicator} Geographic Distribution")
            map_fig = self.create_interactive_map(gdf_filtered, selected_indicator)
            if map_fig:
                st.plotly_chart(map_fig, use_container_width=True)
        
        with col2:
            # Display category analysis
            st.markdown(f"### 📊 CoC Category Analysis")
            category_fig = self.create_category_analysis(gdf_filtered, selected_indicator)
            st.plotly_chart(category_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Trend analysis and state comparison
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("### 📈 Time Trend Analysis")
            trend_fig = self.create_trend_analysis(self.gdf, selected_states, selected_indicator)
            st.plotly_chart(trend_fig, use_container_width=True)
        
        with col4:
            st.markdown("### 🏆 State Ranking Comparison")
            comparison_fig = self.create_state_comparison(gdf_filtered, selected_indicator)
            st.plotly_chart(comparison_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Correlation analysis
        st.markdown("### 🔗 Indicator Correlation Analysis")
        correlation_fig = self.create_correlation_analysis(gdf_filtered)
        st.plotly_chart(correlation_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed data table
        st.markdown("### 📋 Detailed Data Table")
        
        # Select columns to display
        display_cols = ['State', 'CoC Number', 'CoC Name', 'CoC Category', 'Region', 'Division']
        display_cols.extend([col for col in self.homeless_indicators if col in gdf_filtered.columns])
        
        # Display data table
        st.dataframe(
            gdf_filtered[display_cols].round(0),
            use_container_width=True,
            height=400
        )
        
        # Data export functionality
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # Export filtered data
            csv_data = gdf_filtered.drop('geometry', axis=1).to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Data (CSV)",
                data=csv_data,
                file_name=f"coc_data_{selected_year}_{selected_indicator}.csv",
                mime="text/csv"
            )
        
        with col_export2:
            # Export summary statistics
            summary_stats = gdf_filtered.groupby(['State', 'CoC Category'])[self.homeless_indicators].sum().reset_index()
            summary_csv = summary_stats.to_csv(index=False)
            st.download_button(
                label="📊 Download Summary Statistics (CSV)",
                data=summary_csv,
                file_name=f"coc_summary_{selected_year}.csv",
                mime="text/csv"
            )
        
        # Footer information
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; margin-top: 2rem;'>
            <p><b>💡 Usage Tips:</b></p>
            <p>• Hover over markers on the map to view detailed information</p>
            <p>• Use the left control panel to filter different years, states, and indicators</p>
            <p>• Time trend analysis shows annual changes in selected indicators</p>
            <p>• Correlation analysis helps understand relationships between different indicators</p>
            <hr style='margin: 1rem 0;'>
            <p style='font-size: 0.9rem;'>Data Source: HUD Continuum of Care (CoC) Data | System Developed by: Enhanced CoC Visualizer</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    visualizer = EnhancedCoCVisualizer()
    visualizer.run() 