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

# Streamlit version compatibility handling
def safe_rerun():
    """Safe rerun function, compatible with different versions of Streamlit"""
    try:
        if hasattr(st, 'rerun'):
            st.rerun()
        elif hasattr(st, 'experimental_rerun'):
            st.experimental_rerun()
        else:
            # For very old versions, use session state changes to trigger rerun
            st.session_state._rerun_trigger = not st.session_state.get('_rerun_trigger', False)
    except Exception:
        # If all methods fail, handle silently
        pass

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
    .map-container {
        position: relative;
        margin-top: 10px;
    }
    /* Optimize sidebar button display in narrow width */
    .sidebar .element-container button {
        font-size: 0.85rem !important;
        padding: 0.25rem 0.5rem !important;
        width: 100% !important;
        text-align: center !important;
    }
    /* Optimize slider label display */
    .sidebar .stSlider > label {
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    /* Optimize number input box */
    .sidebar .stNumberInput > label {
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
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
            'Unsheltered Chronically Homeless Individuals',
            'Total Year-Round Beds (ES, TH, SH)',
            'Total Year-Round Beds (ES)',
            'Total Year-Round Beds (TH)',
            'Total Year-Round Beds (SH)'
        ]
        
        # Initialize session state for timeline controls - will be set to 2024 in run()
        if 'current_year_index' not in st.session_state:
            st.session_state.current_year_index = 999  # Flag for first initialization (will be reset to latest year)
        
    @st.cache_data
    def load_data(_self):
        """Load GPKG geographic data"""
        try:
            gdf = gpd.read_file("Final_CoC_Time_Data_with_Beds_Corrected_SH.gpkg")
            
            # Data cleaning - remove NaN years first
            gdf = gdf.dropna(subset=['CoC Number', 'CoC Name', 'Year'])
            
            # Remove any remaining NaN values in Year column
            gdf = gdf[gdf['Year'].notna()]
            
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
    
    def create_interactive_map(self, gdf_filtered, selected_indicator, selected_year):
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
            text += f"Unsheltered: {row['Unsheltered Homeless']:,.0f}<br>"
            
            # Add bed information if available
            if 'Total Year-Round Beds (ES, TH, SH)' in row.index:
                text += f"<br><b>Bed Information:</b><br>"
                text += f"Total Beds (ES+TH+SH): {row.get('Total Year-Round Beds (ES, TH, SH)', 0):,.0f}<br>"
                text += f"Emergency Shelter Beds (ES): {row.get('Total Year-Round Beds (ES)', 0):,.0f}<br>"
                text += f"Transitional Housing Beds (TH): {row.get('Total Year-Round Beds (TH)', 0):,.0f}<br>"
                text += f"Safe Haven Beds (SH): {row.get('Total Year-Round Beds (SH)', 0):,.0f}"
                
            hover_text.append(text)
        
        # Calculate marker size and color
        values = gdf_filtered[selected_indicator]
        # Ensure values are numeric type, handle NaN values
        values = pd.to_numeric(values, errors='coerce').fillna(0).values
        
        # Avoid division by zero error
        max_val = max(values) if len(values) > 0 and max(values) > 0 else 1
        min_val = min(values) if len(values) > 0 else 0
        
        # Marker size (10-50 pixels for larger map)
        if max_val > min_val:
            sizes = 10 + (values - min_val) / (max_val - min_val) * 40
        else:
            sizes = np.full(len(values), 20)  # Default size
        sizes = np.clip(sizes, 10, 50)
        
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
                    title=selected_indicator,
                    thickness=15,
                    len=0.7
                ),
                opacity=0.8
            ),
            text=hover_text,
            hovertemplate='%{text}<extra></extra>',
            name='CoC Areas'
        ))
        
        # Map layout - larger size for full row with smooth transitions
        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=3.5
            ),
            height=800,  # Increased height for larger map
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=False,
            title=dict(
                text=f"{selected_indicator} Geographic Distribution - {selected_year}",
                x=0.5,
                y=0.98,
                xanchor='center',
                yanchor='top',
                font=dict(size=20, color='#1f4e79')
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=16,
                font_family="Arial",
                font_color="black",
                bordercolor="gray"
            ),
            transition=dict(
                duration=800,
                easing="cubic-in-out"
            ),
            uirevision=selected_year  # Maintain map state during updates
        )
        
        return fig
    
    def create_summary_metrics(self, gdf_filtered):
        """Create summary metrics cards"""
        current_year = gdf_filtered['Year'].iloc[0]
        
        # Current year data
        total_cocs = len(gdf_filtered)
        total_homeless = gdf_filtered['Overall Homeless'].sum()
        total_sheltered = gdf_filtered['Sheltered Total Homeless'].sum()
        total_unsheltered = gdf_filtered['Unsheltered Homeless'].sum()
        total_individuals = gdf_filtered['Overall Homeless Individuals'].sum()
        total_families = gdf_filtered['Overall Homeless People in Families'].sum()
        total_chronic = gdf_filtered['Overall Chronically Homeless Individuals'].sum()
        family_households = gdf_filtered['Overall Homeless Family Households'].sum()
        
        # Calculate composition percentages
        sheltered_pct = (total_sheltered / total_homeless * 100) if total_homeless > 0 else 0
        unsheltered_pct = (total_unsheltered / total_homeless * 100) if total_homeless > 0 else 0
        individuals_pct = (total_individuals / total_homeless * 100) if total_homeless > 0 else 0
        families_pct = (total_families / total_homeless * 100) if total_homeless > 0 else 0
        chronic_pct = (total_chronic / total_homeless * 100) if total_homeless > 0 else 0
        
        # Calculate year-over-year changes
        def get_yoy_change(current_val, indicator, states=None, categories=None):
            # Don't show YoY change for 2007 (first year)
            if current_year <= 2007:
                return ""
            
            try:
                prev_year = current_year - 1
                prev_data = self.gdf[self.gdf['Year'] == prev_year].copy()
                
                # Apply same filters as current data
                if states:
                    prev_data = prev_data[prev_data['State'].isin(states)]
                if categories:
                    prev_data = prev_data[prev_data['CoC Category'].isin(categories)]
                
                if len(prev_data) > 0:
                    prev_val = prev_data[indicator].sum()
                    if prev_val > 0:
                        change_pct = ((current_val - prev_val) / prev_val) * 100
                        color = "#09ab3b" if change_pct >= 0 else "#dc2626"
                        return f"<span style='color: {color};'>{change_pct:+.1f}%</span>"
                return "<span style='color: #64748b;'>N/A</span>"
            except:
                return "<span style='color: #64748b;'>N/A</span>"
        
        # Get filter states and categories for YoY calculation
        filter_states = None
        filter_categories = None
        if hasattr(self, '_current_filter_states'):
            filter_states = self._current_filter_states
        if hasattr(self, '_current_filter_categories'):
            filter_categories = self._current_filter_categories
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Total CoC Areas</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>{total_cocs:,}</div>
                <div style='height: 20px;'></div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            yoy_homeless = get_yoy_change(total_homeless, 'Overall Homeless', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Total Homeless</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>{total_homeless:,.0f}</div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_homeless}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            yoy_sheltered = get_yoy_change(total_sheltered, 'Sheltered Total Homeless', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Sheltered</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>
                    {total_sheltered:,.0f} <span style='font-size: 0.875rem; color: #64748b;'>({sheltered_pct:.1f}%)</span>
                </div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_sheltered}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            yoy_unsheltered = get_yoy_change(total_unsheltered, 'Unsheltered Homeless', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Unsheltered</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>
                    {total_unsheltered:,.0f} <span style='font-size: 0.875rem; color: #64748b;'>({unsheltered_pct:.1f}%)</span>
                </div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_unsheltered}</div>
            </div>
            """, unsafe_allow_html=True)
        
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            yoy_individuals = get_yoy_change(total_individuals, 'Overall Homeless Individuals', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Individuals</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>
                    {total_individuals:,.0f} <span style='font-size: 0.875rem; color: #64748b;'>({individuals_pct:.1f}%)</span>
                </div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_individuals}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col6:
            yoy_families = get_yoy_change(total_families, 'Overall Homeless People in Families', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>People in Families</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>
                    {total_families:,.0f} <span style='font-size: 0.875rem; color: #64748b;'>({families_pct:.1f}%)</span>
                </div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_families}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col7:
            yoy_chronic = get_yoy_change(total_chronic, 'Overall Chronically Homeless Individuals', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Chronically Homeless</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>
                    {total_chronic:,.0f} <span style='font-size: 0.875rem; color: #64748b;'>({chronic_pct:.1f}%)</span>
                </div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_chronic}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col8:
            yoy_households = get_yoy_change(family_households, 'Overall Homeless Family Households', filter_states, filter_categories)
            st.markdown(f"""
            <div style='background-color: white; padding: 1.2rem; border-radius: 0.5rem; border: 1px solid #e1e5e9; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                <div style='color: #262730; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;'>Family Households</div>
                <div style='color: #262730; font-size: 1.875rem; font-weight: 700; line-height: 1;'>{family_households:,.0f}</div>
                <div style='font-size: 0.875rem; height: 20px; display: flex; align-items: center;'>{yoy_households}</div>
            </div>
            """, unsafe_allow_html=True)
    
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
            markers=True,
            line_shape='spline'
        )
        
        fig.update_layout(
            height=400,
            xaxis_title="Year",
            yaxis_title=selected_indicator,
            title=dict(
                text=title,
                x=0.5,
                y=0.95,
                xanchor='center',
                yanchor='top',
                font=dict(size=18, color='#1f4e79', family='Arial')
            ),
            font=dict(family='Arial', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=50, t=80, b=50),
            hoverlabel=dict(
                bgcolor="white",
                font_size=16,
                font_family="Arial",
                font_color="black",
                bordercolor="gray"
            )
        )
        
        return fig
    
    def create_state_comparison(self, gdf_filtered, selected_indicator):
        """Create state comparison chart"""
        state_stats = gdf_filtered.groupby('State')[selected_indicator].sum().sort_values(ascending=False).head(15)
        
        fig = px.bar(
            x=state_stats.values,
            y=state_stats.index,
            orientation='h',
            labels={'x': selected_indicator, 'y': 'State'},
            color=state_stats.values,
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            height=500,
            title=dict(
                text=f"Top 15 States by {selected_indicator}",
                x=0.5,
                y=0.95,
                xanchor='center',
                yanchor='top',
                font=dict(size=18, color='#1f4e79', family='Arial')
            ),
            font=dict(family='Arial', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=80, r=50, t=80, b=50),
            hoverlabel=dict(
                bgcolor="white",
                font_size=16,
                font_family="Arial",
                font_color="black",
                bordercolor="gray"
            )
        )
        
        return fig
    
    def create_category_analysis(self, gdf_filtered, selected_indicator):
        """Create CoC category analysis"""
        category_stats = gdf_filtered.groupby('CoC Category')[selected_indicator].sum()
        
        # Create color palette
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        
        fig = px.pie(
            values=category_stats.values,
            names=category_stats.index,
            color_discrete_sequence=colors,
            hole=0.3  # Creates a donut chart for better visual appeal
        )
        
        # Update traces for better styling
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont=dict(size=12, color='white', family='Arial'),
            marker=dict(
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b style="font-size:16px">%{label}</b><br>' +
                         '<span style="font-size:14px">Value: %{value:,.0f}</span><br>' +
                         '<span style="font-size:14px">Percentage: %{percent}</span><br>' +
                         '<extra></extra>',
            pull=[0.05 if i == category_stats.values.argmax() else 0 for i in range(len(category_stats))]  # Pull out the largest slice
        )
        
        fig.update_layout(
            height=500,
            title=dict(
                text=f"CoC Category {selected_indicator} Distribution",
                x=0.5,
                y=0.95,
                xanchor='center',
                yanchor='top',
                font=dict(size=18, color='#1f4e79', family='Arial')
            ),
            font=dict(family='Arial', size=12),
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.05,
                font=dict(size=11)
            ),
            margin=dict(l=20, r=120, t=80, b=20),
            showlegend=True,
            plot_bgcolor='white',
            paper_bgcolor='white',
            hoverlabel=dict(
                bgcolor="white",
                font_size=16,
                font_family="Arial",
                font_color="black",
                bordercolor="gray"
            )
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
        # Convert to absolute values for 0-1 range (correlation strength)
        abs_correlation_data = correlation_data.abs()
        
        fig = px.imshow(
            abs_correlation_data,
            color_continuous_scale=[[0, '#f7f7f7'], [0.2, '#c6dbef'], [0.4, '#6baed6'], [0.6, '#3182bd'], [0.8, '#08519c'], [1, '#08306b']],
            aspect="auto",
            text_auto=False,  # Disable auto text to use custom annotations
            zmin=0,
            zmax=1
        )
        
        # Add correlation values as text annotations with dynamic color
        fig.update_traces(
            text=[],  # Remove default text to avoid overlap
            hovertemplate='<b style="font-size:16px">%{x}</b> vs <b style="font-size:16px">%{y}</b><br>' +
                         '<span style="font-size:14px">Correlation Strength: %{z:.2f}</span><extra></extra>'
        )
        
        # Update text color based on correlation strength for better readability
        for i in range(len(abs_correlation_data.index)):
            for j in range(len(abs_correlation_data.columns)):
                abs_corr_val = abs_correlation_data.iloc[i, j]
                # Use dark text for light colors (low correlation), white text for dark colors (high correlation)
                text_color = 'white' if abs_corr_val > 0.5 else 'black'
                fig.add_annotation(
                    x=j, y=i,
                    text=f"{abs_corr_val:.2f}",
                    showarrow=False,
                    font=dict(color=text_color, size=11, family='Arial')
                )
        
        fig.update_layout(
            height=500,
            title=dict(
                text="Key Indicators Correlation Strength Analysis",
                x=0.5,
                y=0.95,
                xanchor='center',
                yanchor='top',
                font=dict(size=18, color='#1f4e79', family='Arial')
            ),
            font=dict(family='Arial', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=50, r=150, t=80, b=50),
            hoverlabel=dict(
                bgcolor="white",
                font_size=16,
                font_family="Arial",
                font_color="black",
                bordercolor="gray"
            )
        )
        
        # Update colorbar for better professional appearance
        fig.update_coloraxes(
            colorbar=dict(
                title=dict(
                    text="Correlation<br>Strength",
                    font=dict(size=12, family='Arial')
                ),
                tickvals=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                ticktext=['0.0', '0.2', '0.4', '0.6', '0.8', '1.0'],
                tickfont=dict(size=11, family='Arial'),
                len=0.8,
                thickness=20
            )
        )
        
        return fig

    def create_shelter_homeless_correlation_map(self, _gdf, selected_year):
        """Create correlation map between shelter facility number and homeless number"""
        try:
            import numpy as np  # Import numpy at function start
            import pandas as pd  # Import pandas at function start
            st.subheader(f"📊 Shelter Facility & Homeless Correlation Analysis ({selected_year})")
            st.info(f"🔔 **Analysis Description**: Shows the correlation between total shelter bed capacity and homeless population for {selected_year}.")
            st.write("Analyzes the relationship between shelter facility capacity and homeless numbers by CoC area")
            

            
            # Step 1: Get current year data and calculate correlation metrics
            st.write(f"Analyzing correlation data for {selected_year}...")
            
            # Get current year data
            current_data = _gdf[_gdf['Year'] == selected_year].copy()
            
            if len(current_data) == 0:
                st.warning(f"No data found for {selected_year}")
                return None
            
            # Prepare correlation analysis data
            correlation_data = current_data[['CoC Number', 'CoC Name', 'State', 'geometry']].copy()
            
            # Add bed data
            if 'Total Year-Round Beds (ES, TH, SH)' in current_data.columns:
                correlation_data['Total_Beds'] = pd.to_numeric(current_data['Total Year-Round Beds (ES, TH, SH)'], errors='coerce').fillna(0)
            else:
                correlation_data['Total_Beds'] = 0
            
            # Add homeless population data
            if 'Overall Homeless' in current_data.columns:
                correlation_data['Total_Homeless'] = pd.to_numeric(current_data['Overall Homeless'], errors='coerce').fillna(0)
            else:
                correlation_data['Total_Homeless'] = 0
                
            # Add sheltered homeless data
            if 'Sheltered Total Homeless' in current_data.columns:
                correlation_data['Sheltered_Homeless'] = pd.to_numeric(current_data['Sheltered Total Homeless'], errors='coerce').fillna(0)
            else:
                correlation_data['Sheltered_Homeless'] = 0
                
            # Add unsheltered homeless data
            if 'Unsheltered Homeless' in current_data.columns:
                correlation_data['Unsheltered_Homeless'] = pd.to_numeric(current_data['Unsheltered Homeless'], errors='coerce').fillna(0)
            else:
                correlation_data['Unsheltered_Homeless'] = 0
            
            # Calculate bed utilization rate (if possible)
            correlation_data['Bed_Utilization_Rate'] = np.where(
                correlation_data['Total_Beds'] > 0,
                (correlation_data['Sheltered_Homeless'] / correlation_data['Total_Beds']) * 100,
                0
            )
            
            # Calculate bed gap
            correlation_data['Bed_Gap'] = correlation_data['Total_Homeless'] - correlation_data['Total_Beds']
            
            # Remove invalid data
            correlation_data = correlation_data.dropna(subset=['Total_Beds', 'Total_Homeless'])
            
            # Step 2: Calculate adaptive classification thresholds (without displaying)
            # Calculate percentiles for adaptive thresholds
            beds_percentiles = correlation_data['Total_Beds'].quantile([0.25, 0.5, 0.75]).tolist()
            homeless_percentiles = correlation_data['Total_Homeless'].quantile([0.25, 0.5, 0.75]).tolist()
            
            def classify_beds_capacity(beds):
                if beds == 0:
                    return 'B0'  # No beds
                elif beds <= beds_percentiles[0]:  # Bottom 25%
                    return 'B1'  # Low capacity
                elif beds <= beds_percentiles[2]:  # 25%-75%
                    return 'B2'  # Medium capacity
                else:  # Top 25%
                    return 'B3'  # High capacity
            
            def classify_homeless_population(homeless):
                if homeless == 0:
                    return 'H0'  # No homeless
                elif homeless <= homeless_percentiles[0]:  # Bottom 25%
                    return 'H1'  # Low population
                elif homeless <= homeless_percentiles[2]:  # 25%-75%
                    return 'H2'  # Medium population
                else:  # Top 25%
                    return 'H3'  # High population
            
            correlation_data['Beds_Class'] = correlation_data['Total_Beds'].apply(classify_beds_capacity)
            correlation_data['Homeless_Class'] = correlation_data['Total_Homeless'].apply(classify_homeless_population)
            correlation_data['Correlation_Class'] = correlation_data['Beds_Class'] + '-' + correlation_data['Homeless_Class']
            
            # Step 3: Create improved classification based on bed gap ratio
            correlation_data['Bed_Gap_Percentage'] = np.where(
                correlation_data['Total_Homeless'] > 0,
                (correlation_data['Bed_Gap'] / correlation_data['Total_Homeless']) * 100,
                0
            )
            
            # Calculate adaptive thresholds for bed gap ratio
            gap_percentiles = correlation_data['Bed_Gap_Percentage'].quantile([0.2, 0.4, 0.6, 0.8]).tolist()
            
            def classify_need_level(gap_percentage, total_homeless):
                if total_homeless == 0:
                    return 'NO_DATA'  # No homeless population
                elif gap_percentage <= gap_percentiles[0]:  # Bottom 20% - best situations
                    return 'EXCELLENT'  # Bed surplus or minimal gap
                elif gap_percentage <= gap_percentiles[1]:  # 20%-40%
                    return 'GOOD'  # Manageable gap
                elif gap_percentage <= gap_percentiles[2]:  # 40%-60%
                    return 'MODERATE'  # Moderate shortage
                elif gap_percentage <= gap_percentiles[3]:  # 60%-80%
                    return 'HIGH'  # High need
                else:  # Top 20% - worst situations
                    return 'CRITICAL'  # Critical shortage
            
            correlation_data['Need_Level'] = correlation_data.apply(
                lambda row: classify_need_level(row['Bed_Gap_Percentage'], row['Total_Homeless']), axis=1
            )
            
            # Define improved color scheme based on need levels
            need_colors = {
                'NO_DATA': '#f0f0f0',      # Light gray - No data
                'EXCELLENT': '#006d2c',    # Dark green - Surplus/minimal gap  
                'GOOD': '#31a354',         # Green - Good situation
                'MODERATE': '#fdcc8a',     # Light orange - Moderate need
                'HIGH': '#fc8d59',         # Orange - High need
                'CRITICAL': '#d94701'      # Dark red - Critical need
            }
            
            # Add colors to data
            correlation_data['Color'] = correlation_data['Need_Level'].map(need_colors)
            
            # Create map
            try:
                centroids = correlation_data.geometry.centroid
                lats = [point.y if hasattr(point, 'y') else 39.8283 for point in centroids]
                lons = [point.x if hasattr(point, 'x') else -98.5795 for point in centroids]
            except Exception as e:
                st.warning(f"Geometric data processing error: {str(e)}")
                lats = [39.8283] * len(correlation_data)
                lons = [-98.5795] * len(correlation_data)
            
            # Create simplified hover text
            hover_text = []
            for _, row in correlation_data.iterrows():
                # Create concise hover display focusing on key information
                text = f"<b>{row['CoC Name']}</b><br>"
                text += f"<b>State:</b> {row['State']}<br>"
                text += f"<b>Total Beds:</b> {row['Total_Beds']:,.0f}<br>"
                text += f"<b>Homeless Population:</b> {row['Total_Homeless']:,.0f}<br>"
                
                # Show bed status
                if row['Bed_Gap'] >= 0:
                    bed_status = f"Shortage of {row['Bed_Gap']:,.0f} beds"
                else:
                    bed_status = f"Surplus of {abs(row['Bed_Gap']):,.0f} beds"
                text += f"<b>Bed Status:</b> {bed_status}<br>"
                
                # Show gap percentage
                text += f"<b>Gap Ratio:</b> {row['Bed_Gap_Percentage']:+.1f}%<br>"
                
                # Show need level with color
                need_level_display = {
                    'NO_DATA': '⚪ No Data',
                    'EXCELLENT': '🟢 Excellent',
                    'GOOD': '🟢 Good',
                    'MODERATE': '🟡 Moderate Need',
                    'HIGH': '🟠 High Need',
                    'CRITICAL': '🔴 Critical Need'
                }
                text += f"<b>Need Level:</b> {need_level_display.get(row['Need_Level'], row['Need_Level'])}"
                
                hover_text.append(text)
            
            # Create chart showing individual data points
            fig = go.Figure()
            
            # Add all individual CoC data points
            fig.add_trace(go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode='markers',
                marker=dict(
                    size=8,
                    color=correlation_data['Color'],
                    opacity=0.8,
                    symbol='circle'
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name='CoC Areas',
                showlegend=False
            ))
            

            
            # Perform clustering analysis for statistics (but don't show cluster circles)
            try:
                from sklearn.cluster import KMeans
                from sklearn.preprocessing import StandardScaler
                import numpy as np
                
                # Calculate additional metrics for clustering
                correlation_data['Bed_Gap_Ratio'] = np.where(
                    correlation_data['Total_Homeless'] > 0,
                    correlation_data['Bed_Gap'] / correlation_data['Total_Homeless'],
                    0
                )
                
                correlation_data['Need_Pressure'] = np.where(
                    correlation_data['Total_Beds'] > 0,
                    correlation_data['Total_Homeless'] / correlation_data['Total_Beds'],
                    10
                )
                
                # Create comprehensive need score based on new classification
                need_level_scores = {
                    'NO_DATA': 0, 'EXCELLENT': 1, 'GOOD': 2, 
                    'MODERATE': 3, 'HIGH': 4, 'CRITICAL': 5
                }
                
                correlation_data['Color_Need_Score'] = correlation_data['Need_Level'].map(need_level_scores).fillna(0)
                
                # Perform clustering analysis
                cluster_features = np.column_stack([
                    correlation_data['Color_Need_Score'].values,
                    correlation_data['Bed_Utilization_Rate'].values,
                    correlation_data['Bed_Gap_Ratio'].values
                ])
                
                if len(cluster_features) >= 3:
                    scaler = StandardScaler()
                    scaled_features = scaler.fit_transform(cluster_features)
                    
                    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(scaled_features)
                    correlation_data['Cluster'] = cluster_labels
                    
                    # Map clusters to need levels
                    cluster_stats = []
                    for i in range(3):
                        cluster_data = correlation_data[correlation_data['Cluster'] == i]
                        if len(cluster_data) > 0:
                            avg_need_score = cluster_data['Color_Need_Score'].mean()
                            cluster_stats.append((i, avg_need_score, len(cluster_data)))
                    
                    cluster_stats.sort(key=lambda x: x[1], reverse=True)
                    cluster_mapping = {original_id: rank for rank, (original_id, _, _) in enumerate(cluster_stats)}
                    correlation_data['Need_Level'] = correlation_data['Cluster'].map(cluster_mapping)
                    
                    cluster_success = True
                else:
                    cluster_success = False
                    
            except Exception:
                cluster_success = False
            
            # Add original individual data points
            fig.add_trace(go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode='markers',
                marker=dict(
                    size=8,
                    color=correlation_data['Color'],
                    opacity=0.8,
                    symbol='circle'
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name='CoC Areas',
                showlegend=False
            ))
            
            fig.update_layout(
                mapbox=dict(
                    style="carto-positron",  # More stable style
                    center=dict(lat=39.8283, lon=-98.5795),
                    zoom=3.5,
                    accesstoken=None  # Use free version to avoid token issues
                ),
                height=700,
                margin=dict(l=0, r=0, t=50, b=0),
                showlegend=False,
                title=dict(
                    text=f"Shelter Capacity vs Homeless Population Analysis ({selected_year})",
                    x=0.5,
                    y=0.98,
                    xanchor='center',
                    yanchor='top',
                    font=dict(size=18, color='#1f4e79')
                )
            )
            
            # Add comprehensive classification explanation
            with st.expander("📊 Adaptive Classification System Details", expanded=False):
                st.markdown("""
                ### 🎯 Bed Gap Ratio-Based Adaptive Classification:
                
                **Classification Method**: Bed Gap Ratio = (Homeless Population - Bed Capacity) / Homeless Population × 100%
                
                **Adaptive Thresholds** (Based on current year data distribution quintiles):
                """)
                
                st.write(f"- **🟢 Excellent**: Gap ratio ≤ {gap_percentiles[0]:.1f}% (Top 20% best situations)")
                st.write(f"- **🟢 Good**: Gap ratio {gap_percentiles[0]:.1f}% - {gap_percentiles[1]:.1f}% (20%-40%)")
                st.write(f"- **🟡 Moderate**: Gap ratio {gap_percentiles[1]:.1f}% - {gap_percentiles[2]:.1f}% (40%-60%)")
                st.write(f"- **🟠 High Need**: Gap ratio {gap_percentiles[2]:.1f}% - {gap_percentiles[3]:.1f}% (60%-80%)")
                st.write(f"- **🔴 Critical**: Gap ratio > {gap_percentiles[3]:.1f}% (Bottom 20% worst situations)")
                st.write(f"- **⚪ No Data**: No homeless population")
                
                # Show current distribution
                level_counts = correlation_data['Need_Level'].value_counts()
                st.markdown("### 📊 Current Distribution Statistics:")
                for level in ['EXCELLENT', 'GOOD', 'MODERATE', 'HIGH', 'CRITICAL', 'NO_DATA']:
                    count = level_counts.get(level, 0)
                    percentage = (count / len(correlation_data)) * 100 if len(correlation_data) > 0 else 0
                    color_icon = {'EXCELLENT': '🟢', 'GOOD': '🟢', 'MODERATE': '🟡', 'HIGH': '🟠', 'CRITICAL': '🔴', 'NO_DATA': '⚪'}[level]
                    st.write(f"{color_icon} **{level}**: {count} areas ({percentage:.1f}%)")
                
                st.markdown("""
                ### 📈 Classification Advantages:
                - **Adaptive**: Thresholds based on actual data distribution, ensuring balanced category sizes
                - **Relative Comparison**: Identifies relatively best and worst performing areas
                - **Intuitive Understanding**: Gap ratio directly reflects urgency of bed shortage
                - **Balanced Distribution**: Avoids concentration of all areas in single category
                """)
            
            # Add simplified legend above the chart  
            st.markdown(f"""
            **📊 Map Legend (Adaptive Classification Based on {selected_year} Data):**  
            **Each dot = One CoC area** (Original data, not cluster circles)  
            🟢 Excellent/Good (≤{gap_percentiles[1]:.1f}% gap) | 🟡 Moderate Need | 🟠 High Need | 🔴 Critical | ⚪ No Data
            """)
            
            # Display map with enhanced error handling
            try:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            except Exception as plot_error:
                st.warning(f"🗺️ 地图渲染遇到问题，切换到简化视图")
                
                # Create simplified scatter plot as backup
                simple_fig = go.Figure()
                simple_fig.add_trace(go.Scatter(
                    x=lons,
                    y=lats,
                    mode='markers',
                    marker=dict(
                        size=10,
                        color=correlation_data['Color'],
                        opacity=0.8,
                        line=dict(width=1, color='white')
                    ),
                    text=hover_text,
                    hovertemplate='%{text}<extra></extra>',
                    name='CoC Areas'
                ))
                simple_fig.update_layout(
                    title=f"Shelter Capacity vs Homeless Population Analysis ({selected_year}) - 简化视图",
                    xaxis_title="经度 (Longitude)",
                    yaxis_title="纬度 (Latitude)",
                    height=500,
                    plot_bgcolor='rgba(240,240,240,0.3)',
                    showlegend=False
                )
                st.plotly_chart(simple_fig, use_container_width=True)
            
                            # Create legend and statistics (table format)
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("🎨 Correlation Legend")
                    
                    # Map legend
                    st.write("**🗺️ Map Legend:**")
                    st.write("• **Individual CoCs**: Each point represents one CoC area")
                    st.write("• **Point Color**: Based on bed capacity and homeless population combination")
                    st.markdown("---")
                    
                    st.write("**Bed Capacity Categories:**")
                    st.write("- B0: No beds (0)")
                    st.write("- B1: Low capacity (1-500)")
                    st.write("- B2: Medium capacity (501-2000)")
                    st.write("- B3: High capacity (>2000)")
                    
                    st.write("**Homeless Population Categories:**")
                    st.write("- H0: No homeless (0)")
                    st.write("- H1: Low population (1-500)")
                    st.write("- H2: Medium population (501-2000)")
                    st.write("- H3: High population (>2000)")
                    
                    # Create comprehensive color legend table
                    st.write("**Complete Color Legend:**")
                    
                    # Enhanced legend with need level analysis
                    legend_table_data = []
                    need_level_mapping = {
                        ('B0', 'H1'): '🔴 Critical Need', ('B0', 'H2'): '🔴 Critical Need', ('B0', 'H3'): '🔴 Critical Need',
                        ('B1', 'H2'): '🔴 High Need', ('B1', 'H3'): '🔴 High Need', ('B2', 'H3'): '🔴 High Need',
                        ('B1', 'H1'): '🟠 Medium Need', ('B2', 'H2'): '🟠 Medium Need', ('B3', 'H3'): '🟠 Medium Need',
                        ('B2', 'H1'): '🟢 Good Match', ('B3', 'H2'): '🟢 Good Match',
                        ('B3', 'H1'): '🔵 Oversupply',
                        ('B0', 'H0'): '⚪ No Data', ('B1', 'H0'): '⚪ No Data', ('B2', 'H0'): '⚪ No Data', ('B3', 'H0'): '⚪ No Data'
                    }
                    
                    for category, color in correlation_colors.items():
                        beds_class, homeless_class = category.split('-')
                        beds_desc = {"B0": "No Beds (0)", "B1": "Low (1-500)", "B2": "Medium (501-2K)", "B3": "High (>2K)"}[beds_class]
                        homeless_desc = {"H0": "None (0)", "H1": "Low (1-500)", "H2": "Medium (501-2K)", "H3": "High (>2K)"}[homeless_class]
                        need_level = need_level_mapping.get((beds_class, homeless_class), '❓ Unknown')
                        
                        legend_table_data.append({
                            "分类": category,
                            "床位容量": beds_desc,
                            "无家可归人口": homeless_desc,
                            "需求等级": need_level,
                            "颜色": f'<span style="color: {color}; font-size: 20px;">●</span>'
                        })
                    
                    legend_df = pd.DataFrame(legend_table_data)
                    st.markdown(legend_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                    
                    # Add summary by need level
                    st.write("**需求等级统计:**")
                    class_counts = correlation_data['Correlation_Class'].value_counts()
                    need_summary = {}
                    for category, count in class_counts.items():
                        beds_class, homeless_class = category.split('-')
                        need_level = need_level_mapping.get((beds_class, homeless_class), '❓ Unknown')
                        need_summary[need_level] = need_summary.get(need_level, 0) + count
                    
                    for need_level, count in sorted(need_summary.items()):
                        st.write(f"• {need_level}: {count} 个CoC区域")
                
                with col2:
                    st.subheader("📊 Correlation Statistics")
                    
                    # Show clustering results if available
                    if cluster_success and 'Need_Level' in correlation_data.columns:
                        st.write("**🎯 Clustering Analysis Results:**")
                        need_level_names = ['🔴 High Need Group', '🟠 Medium Need Group', '🟢 Low Need Group']
                        for level in range(3):
                            level_data = correlation_data[correlation_data['Need_Level'] == level]
                            if len(level_data) > 0:
                                avg_beds = level_data['Total_Beds'].mean()
                                avg_homeless = level_data['Total_Homeless'].mean()
                                avg_utilization = level_data['Bed_Utilization_Rate'].mean()
                                st.write(f"• {need_level_names[level]}: {len(level_data)} areas")
                                st.write(f"  - Avg beds: {avg_beds:.0f}, Avg homeless: {avg_homeless:.0f}")
                                st.write(f"  - Avg utilization: {avg_utilization:.1f}%")
                        st.markdown("---")
                    
                    # Add timestamp to verify data refresh
                    from datetime import datetime
                    import random
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    analysis_id = random.randint(1000, 9999)
                    st.write(f"🕐 **Analysis Time:** {current_time}")
                    st.write(f"📋 **Analysis ID:** COR-{analysis_id}")
                    
                    # Count statistics for each need level
                    need_counts = correlation_data['Need_Level'].value_counts()
                    total_cocs = len(correlation_data)
                    
                    st.write(f"**Total CoC Count:** {total_cocs}")
                    
                    # Create statistics table for need levels
                    stats_data = []
                    for need_level in ['EXCELLENT', 'GOOD', 'MODERATE', 'HIGH', 'CRITICAL', 'NO_DATA']:
                        count = need_counts.get(need_level, 0)
                        percentage = (count / total_cocs) * 100 if total_cocs > 0 else 0
                        color_hex = need_colors.get(need_level, '#000000')
                        level_display = {
                            'EXCELLENT': 'Excellent',
                            'GOOD': 'Good', 
                            'MODERATE': 'Moderate',
                            'HIGH': 'High Need',
                            'CRITICAL': 'Critical',
                            'NO_DATA': 'No Data'
                        }
                        stats_data.append({
                            "Need Level": level_display.get(need_level, need_level),
                            "Count": count,
                            "Percentage": f"{percentage:.1f}%",
                            "Color": f'<span style="color: {color_hex}; font-size: 16px;">●</span>'
                        })
                    
                    stats_df = pd.DataFrame(stats_data)
                    stats_df = stats_df[stats_df['Count'] > 0]  # Only show categories with data
                    st.markdown("**Need Level Distribution:**")
                    st.markdown(stats_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Show correlation statistics
                total_beds = correlation_data['Total_Beds'].sum()
                total_homeless = correlation_data['Total_Homeless'].sum()
                avg_utilization = correlation_data['Bed_Utilization_Rate'].mean()
                total_gap = correlation_data['Bed_Gap'].sum()
                
                st.write("**Overall Statistics:**")
                overall_stats = pd.DataFrame({
                    "Metric": ["Total Beds", "Total Homeless", "Avg Utilization Rate", "Total Bed Gap"],
                    "Value": [f"{total_beds:,.0f}", f"{total_homeless:,.0f}", f"{avg_utilization:.1f}%", f"{total_gap:+,.0f}"]
                })
                st.markdown(overall_stats.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Show clustering results if available
                if cluster_success and 'Cluster_Mapped' in correlation_data.columns:
                    st.write("**🎯 Optimized Clustering Results Analysis:**")
                    cluster_summary = correlation_data.groupby('Cluster_Mapped').agg({
                        'CoC Number': 'count',
                        'Total_Beds': 'mean',
                        'Total_Homeless': 'mean',
                        'Bed_Gap_Ratio': 'mean',
                        'Need_Pressure': 'mean',
                        'Bed_Utilization_Rate': 'mean',
                        'Combined_Need_Score': 'mean',
                        'Color_Need_Score': 'mean'
                    })
                    
                    cluster_table_data = []
                    # Dynamically obtain cluster labels (3 categories)
                    available_clusters = sorted(correlation_data['Cluster_Mapped'].unique())
                    priority_labels_short = ['🔴 High Need', '⚠️ Medium Need', '✅ Low Need']
                    
                    for cluster_id in available_clusters:
                        if cluster_id in cluster_summary.index:
                            row = cluster_summary.loc[cluster_id]
                            label_idx = min(cluster_id, len(priority_labels_short)-1)
                            cluster_table_data.append({
                                "Need Level": priority_labels_short[label_idx],
                                "CoC Count": int(row['CoC Number']),
                                "Avg Beds": int(row['Total_Beds']),
                                "Avg Homeless": int(row['Total_Homeless']),
                                "Combined Score": f"{row['Combined_Need_Score']:.2f}",
                                "Gap Ratio": f"{row['Bed_Gap_Ratio']:.2f}",
                                "Pressure Index": f"{row['Need_Pressure']:.2f}",
                                "Utilization %": f"{row['Bed_Utilization_Rate']:.1f}%"
                            })
                    
                    cluster_df = pd.DataFrame(cluster_table_data)
                    st.markdown(cluster_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                    
                    # Add clustering algorithm quality report
                    st.write("**📊 Spatial Clustering Algorithm Quality Report:**")
                    quality_metrics = pd.DataFrame({
                        "Metric": ["Cluster Count", "Silhouette Score", "Feature Count", "Standardization", "Spatial Features"],
                        "Value": [f"{best_k} clusters", f"{final_silhouette:.3f}", "5 features (including geographic)", "✅ StandardScaler", "✅ Lat/Lon weighted (×2)"],
                        "Assessment": [
                            "Fixed (3-category system)",
                            "Excellent" if final_silhouette > 0.7 else ("Good" if final_silhouette > 0.5 else "Needs improvement"),
                            "Enhanced with spatial info",
                            "Applied to all features",
                            "Promotes spatial coherence"
                        ]
                    })
                    st.markdown(quality_metrics.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Show best and concerning performing CoCs
                st.write("**🟢 Best Performing Areas (Excellent/Good):**")
                good_match_cocs = correlation_data[correlation_data['Need_Level'].isin(['EXCELLENT', 'GOOD'])]
                if len(good_match_cocs) > 0:
                    for _, coc in good_match_cocs.head(3).iterrows():
                        st.write(f"- {coc['CoC Number']} ({coc['State']}) - Gap: {coc['Bed_Gap_Percentage']:+.1f}%")
                else:
                    st.write("None")
                
                st.write("**🔴 Areas Needing Attention (High/Critical):**")
                high_need_cocs = correlation_data[correlation_data['Need_Level'].isin(['HIGH', 'CRITICAL'])]
                if len(high_need_cocs) > 0:
                    for _, coc in high_need_cocs.head(3).iterrows():
                        st.write(f"- {coc['CoC Number']} ({coc['State']}) - Gap: {coc['Bed_Gap_Percentage']:+.1f}%")
                else:
                    st.write("None")
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating bivariate change map: {str(e)}")
            return None

    def create_bed_capacity_analysis(self, gdf_filtered):
        """Create bed capacity analysis chart with sorting and expand functionality"""
        try:
            # Prepare bed data
            bed_columns = ['Total Year-Round Beds (ES)', 'Total Year-Round Beds (TH)', 'Total Year-Round Beds (SH)']
            available_bed_cols = [col for col in bed_columns if col in gdf_filtered.columns]
            
            if not available_bed_cols:
                fig = go.Figure()
                fig.add_annotation(
                    text="Bed data not available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                fig.update_layout(
                    title="Bed Capacity Analysis",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                return fig
            
            # Calculate total beds by state
            state_bed_data = []
            
            for state in gdf_filtered['State'].unique():
                state_data = gdf_filtered[gdf_filtered['State'] == state]
                
                bed_totals = {}
                for col in available_bed_cols:
                    bed_totals[col] = pd.to_numeric(state_data[col], errors='coerce').sum()
                
                # Add total homeless count for comparison
                if 'Overall Homeless' in state_data.columns:
                    homeless_total = pd.to_numeric(state_data['Overall Homeless'], errors='coerce').sum()
                    bed_totals['Overall Homeless'] = homeless_total
                
                # Calculate total beds
                total_beds = sum([bed_totals.get(col, 0) for col in available_bed_cols])
                bed_totals['Total Beds'] = total_beds
                bed_totals['State'] = state
                state_bed_data.append(bed_totals)
            
            df_beds = pd.DataFrame(state_bed_data)
            
            # Sort by total beds in descending order
            df_beds = df_beds.sort_values('Total Beds', ascending=False)
            
            # Add expand functionality with user control
            expand_option = st.selectbox(
                "📊 Display Options:",
                ["Top 15 States", "Top 25 States", "All States"],
                index=0,
                key="bed_analysis_expand"
            )
            
            if expand_option == "Top 15 States":
                df_display = df_beds.head(15)
            elif expand_option == "Top 25 States":
                df_display = df_beds.head(25)
            else:
                df_display = df_beds
            
            # Create stacked horizontal bar chart
            fig = go.Figure()
            
            colors = {
                'Total Year-Round Beds (ES)': '#FF6B6B',    # Red - Emergency Shelter
                'Total Year-Round Beds (TH)': '#4ECDC4',    # Cyan - Transitional Housing  
                'Total Year-Round Beds (SH)': '#45B7D1',    # Blue - Safe Haven
            }
            
            bed_labels = {
                'Total Year-Round Beds (ES)': 'Emergency Shelter (ES)',
                'Total Year-Round Beds (TH)': 'Transitional Housing (TH)',
                'Total Year-Round Beds (SH)': 'Safe Haven (SH)'
            }
            
            # Reverse order for better visualization (highest at top)
            df_display_reversed = df_display.iloc[::-1]
            
            for col in available_bed_cols:
                if col in df_display_reversed.columns:
                    fig.add_trace(go.Bar(
                        name=bed_labels.get(col, col),
                        y=df_display_reversed['State'],
                        x=df_display_reversed[col],
                        orientation='h',
                        marker_color=colors.get(col, '#95A5A6'),
                        text=[f'{val:,.0f}' if val > 0 else '' for val in df_display_reversed[col]],
                        textposition='inside',
                        textfont=dict(color='white', size=10)
                    ))
            
            # Add total homeless count as reference line (if available)
            if 'Overall Homeless' in df_display_reversed.columns:
                fig.add_trace(go.Scatter(
                    x=df_display_reversed['Overall Homeless'],
                    y=df_display_reversed['State'],
                    mode='markers',
                    name='Total Homeless',
                    marker=dict(
                        symbol='diamond',
                        size=8,
                        color='orange',
                        line=dict(width=2, color='darkorange')
                    ),
                    text=[f'Homeless: {val:,.0f}' for val in df_display_reversed['Overall Homeless']],
                    hovertemplate='%{text}<extra></extra>'
                ))
            
            # Calculate dynamic height based on number of states
            chart_height = max(400, len(df_display) * 25 + 100)
            
            fig.update_layout(
                title=dict(
                    text=f"State Bed Capacity Analysis ({expand_option}) - Sorted by Total Beds",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=16)
                ),
                xaxis_title="Number of Beds",
                yaxis_title="State",
                barmode='stack',
                height=chart_height,
                plot_bgcolor='white',
                paper_bgcolor='white',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                ),
                margin=dict(l=80, r=50, t=80, b=50)
            )
            
            # Add summary statistics
            st.markdown("### 📊 Bed Capacity Summary")
            total_beds_all = df_beds['Total Beds'].sum()
            total_homeless_all = df_beds['Overall Homeless'].sum() if 'Overall Homeless' in df_beds.columns else 0
            avg_beds_per_state = df_beds['Total Beds'].mean()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Beds (All States)", f"{total_beds_all:,.0f}")
            with col2:
                st.metric("Total Homeless (All States)", f"{total_homeless_all:,.0f}")
            with col3:
                st.metric("Avg Beds per State", f"{avg_beds_per_state:,.0f}")
                
            # Display detailed table with expand feature
            with st.expander("📋 View Detailed Bed Capacity Data Table", expanded=False):
                # Create detailed table
                display_table = df_beds[['State', 'Total Beds'] + available_bed_cols + (['Overall Homeless'] if 'Overall Homeless' in df_beds.columns else [])].copy()
                display_table = display_table.round(0)
                
                # Add ranking
                display_table.insert(0, 'Rank', range(1, len(display_table) + 1))
                
                st.dataframe(
                    display_table,
                    use_container_width=True,
                    height=400
                )
                
                # Download option
                csv_data = display_table.to_csv(index=False)
                st.download_button(
                    label="📥 Download Bed Capacity Data (CSV)",
                    data=csv_data,
                    file_name="bed_capacity_analysis.csv",
                    mime="text/csv"
                )
            
            return fig
            
        except Exception as e:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Bed analysis error: {str(e)[:50]}...",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title="Bed Capacity Analysis",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            return fig
    
    def create_sidebar_timeline_controls(self, years):
        """Create timeline controls in sidebar with interactive slider functionality"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🕐 Timeline Control")
        
        # Ensure current_year_index is within bounds
        if st.session_state.current_year_index >= len(years):
            st.session_state.current_year_index = len(years) - 1
        elif st.session_state.current_year_index < 0:
            st.session_state.current_year_index = 0
        
        # Current year display
        current_year = years[st.session_state.current_year_index]
        progress_percentage = ((st.session_state.current_year_index) / (len(years) - 1)) * 100 if len(years) > 1 else 0
        
        st.sidebar.markdown(f"""
        <div style='text-align: center; margin: 1rem 0; background-color: #f0f2f6; padding: 1rem; border-radius: 8px;'>
            <h2 style='color: #1f4e79; font-size: 2rem; margin: 0;'>{current_year}</h2>
            <p style='color: #666; margin: 5px 0; font-size: 0.9rem;'>Current Year ({st.session_state.current_year_index + 1}/{len(years)})</p>
            <div style='width: 100%; height: 6px; background-color: #e0e0e0; border-radius: 3px; margin: 8px 0;'>
                <div style='width: {progress_percentage}%; height: 100%; background-color: #1f4e79; border-radius: 3px; transition: width 0.3s ease;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Year input box with improved compact layout
        year_input = st.sidebar.number_input(
            "Go to Year:",
            min_value=years[0],
            max_value=years[-1],
            value=current_year,
            step=1,
            key="year_input"
        )
        
        # Go button (full width for better narrow sidebar support)
        if st.sidebar.button("📅 Go to Year", key="go_to_year", use_container_width=True):
            if year_input in years:
                st.session_state.current_year_index = years.index(year_input)
                safe_rerun()
            else:
                st.sidebar.error(f"Year {year_input} not available")
        
        # Navigation buttons with compact layout
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("⬅️ Prev", key="prev_year", use_container_width=True):
                if st.session_state.current_year_index > 0:
                    st.session_state.current_year_index -= 1
                safe_rerun()
        
        with col2:
            if st.button("Next ➡️", key="next_year", use_container_width=True):
                if st.session_state.current_year_index < len(years) - 1:
                    st.session_state.current_year_index += 1
                safe_rerun()
        
        # Main year slider - showing actual years instead of indices
        selected_year = st.sidebar.slider(
            "Year Slider:",
            min_value=years[0],
            max_value=years[-1],
            value=current_year,
            step=1,
            key="sidebar_year_slider",
            format="%d"
        )
        
        # Update session state when slider changes
        if selected_year != current_year:
            st.session_state.current_year_index = years.index(selected_year)
        
        # Reset button with compact text
        if st.sidebar.button("🔄 Reset to 2024", key="reset_to_latest", use_container_width=True):
            st.session_state.current_year_index = len(years) - 1
            safe_rerun()
        
        return years[st.session_state.current_year_index]
    
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
        
        # Get available years
        years = sorted(self.gdf['Year'].unique())
        
        # Initialize session state to latest year (2024) if not properly set or first time
        if st.session_state.current_year_index >= len(years) or st.session_state.current_year_index < 0:
            st.session_state.current_year_index = len(years) - 1  # Set to latest year (2024)
        
        # Timeline controls in sidebar
        selected_year = self.create_sidebar_timeline_controls(years)
        
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
        
        # Store current filter states for YoY comparison
        self._current_filter_states = selected_states if selected_states else None
        self._current_filter_categories = selected_categories if selected_categories else None
        
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
        st.markdown(f"""
        <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>📊 {selected_year} Data Overview</h3>
        """, unsafe_allow_html=True)
        self.create_summary_metrics(gdf_filtered)
        
        st.markdown("---")
        
        # Large interactive map with container (full width)
        st.markdown(f"""
        <div class='map-container'>
            <h3 style='text-align: center; color: #1f4e79; margin-bottom: 1rem;'>🗺️ {selected_indicator} Geographic Distribution</h3>
        </div>
        """, unsafe_allow_html=True)
        
        map_fig = self.create_interactive_map(gdf_filtered, selected_indicator, selected_year)
        if map_fig:
            st.plotly_chart(map_fig, use_container_width=True, key=f"map_{selected_year}")
        
        st.markdown("---")
        
        # Create column layout for other charts
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Display category analysis
            st.markdown("""
            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>📊 CoC Category Analysis</h3>
            """, unsafe_allow_html=True)
            category_fig = self.create_category_analysis(gdf_filtered, selected_indicator)
            st.plotly_chart(category_fig, use_container_width=True)
        
        with col2:
            st.markdown("""
            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>🏆 State Ranking Comparison</h3>
            """, unsafe_allow_html=True)
            comparison_fig = self.create_state_comparison(gdf_filtered, selected_indicator)
            st.plotly_chart(comparison_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Add bed capacity analysis if bed data is available
        if any(col.startswith('Total Year-Round Beds') for col in gdf_filtered.columns):
            st.markdown("""
                            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>🛏️ Bed Capacity Analysis</h3>
            """, unsafe_allow_html=True)
            bed_fig = self.create_bed_capacity_analysis(gdf_filtered)
            st.plotly_chart(bed_fig, use_container_width=True)
            st.markdown("---")
            
            # Add shelter-homeless correlation map 
            st.markdown("""
            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>🔗 Shelter Facility & Homeless Correlation Analysis</h3>
            """, unsafe_allow_html=True)
            correlation_fig = self.create_shelter_homeless_correlation_map(self.gdf, selected_year)
            if correlation_fig:
                st.markdown("---")
        
        # Optimized layout: Trend analysis and correlation analysis in one row
        st.markdown("---")
        
        col_trend, col_corr = st.columns([1, 1], gap="medium")
        
        with col_trend:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 1rem;'>
                <h3 style='color: #1f4e79; margin: 0.5rem 0;'>📈 Time Trend Analysis</h3>
            </div>
            """, unsafe_allow_html=True)
            trend_fig = self.create_trend_analysis(self.gdf, selected_states, selected_indicator)
            st.plotly_chart(trend_fig, use_container_width=True)
        
        with col_corr:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 1rem;'>
                <h3 style='color: #1f4e79; margin: 0.5rem 0;'>🔗 Indicator Correlation Analysis</h3>
            </div>
            """, unsafe_allow_html=True)
            correlation_fig = self.create_correlation_analysis(gdf_filtered)
            st.plotly_chart(correlation_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed data table
        st.markdown("""
        <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>📋 Detailed Data Table</h3>
        """, unsafe_allow_html=True)
        
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
            <p>• Use the timeline controller to view data changes across different years</p>
            <p>• The timeline remains visible even when the map is in full screen mode</p>
            <p>• Hover over map markers to view detailed information</p>
            <p>• Use the left control panel to filter different states, indicators, and categories</p>
            <p>• Time trend analysis shows annual changes in selected indicators</p>
            <p>• Correlation analysis helps understand relationships between different indicators</p>
            <hr style='margin: 1rem 0;'>
            <p style='font-size: 0.9rem;'>Data Source: HUD Continuum of Care (CoC) Data | System Developed by: Enhanced CoC Visualizer</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    visualizer = EnhancedCoCVisualizer()
    visualizer.run() 