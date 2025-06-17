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

# Streamlit版本兼容性处理
def safe_rerun():
    """安全的重新运行函数，兼容不同版本的Streamlit"""
    try:
        if hasattr(st, 'rerun'):
            st.rerun()
        elif hasattr(st, 'experimental_rerun'):
            st.experimental_rerun()
        else:
            # 对于非常旧的版本，使用session state变化来触发重新运行
            st.session_state._rerun_trigger = not st.session_state.get('_rerun_trigger', False)
    except Exception:
        # 如果所有方法都失败，静默处理
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
    /* 优化侧边栏按钮在窄宽度下的显示 */
    .sidebar .element-container button {
        font-size: 0.85rem !important;
        padding: 0.25rem 0.5rem !important;
        width: 100% !important;
        text-align: center !important;
    }
    /* 优化滑块标签显示 */
    .sidebar .stSlider > label {
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }
    /* 优化数字输入框 */
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

    def create_bivariate_change_map(self, _gdf, selected_year):
        """Create bivariate choropleth map: Bed capacity vs Unsheltered homeless changes (current year vs previous year)"""
        try:
            if selected_year <= 2007:
                st.subheader("📊 Bivariate Change Analysis Map")
                st.info("🔔 **Note**: 2007 is the baseline year with no previous year data for comparison.")
                return None
            
            previous_year = selected_year - 1
            st.subheader(f"📊 Bivariate Change Analysis Map ({previous_year} → {selected_year})")
            st.info(f"🔔 **Analysis Description**: This analysis shows the change trends of {selected_year} relative to {previous_year}.")
            st.write("Shows the relationship between bed capacity changes and unsheltered homeless population changes")
            
            # Step 1: Calculate percentage change indicators
            st.write(f"Calculating change indicators from {previous_year} to {selected_year}...")
            
            # 获取前一年和当前年数据
            data_previous = _gdf[_gdf['Year'] == previous_year].copy()
            data_current = _gdf[_gdf['Year'] == selected_year].copy()
            
            if len(data_previous) == 0 or len(data_current) == 0:
                st.warning(f"Missing data for {previous_year} or {selected_year}, cannot perform change analysis")
                return None
            
            # 合并数据以计算变化
            change_data = data_previous[['CoC Number', 'CoC Name', 'State', 'geometry', 
                                       'Total Year-Round Beds (ES, TH, SH)', 'Unsheltered Homeless']].merge(
                data_current[['CoC Number', 'Total Year-Round Beds (ES, TH, SH)', 'Unsheltered Homeless']], 
                on='CoC Number', suffixes=(f'_{previous_year}', f'_{selected_year}'), how='inner'
            )
            
            if len(change_data) == 0:
                st.warning(f"No CoC data found that exists in both {previous_year} and {selected_year}")
                return None
            
            # 计算百分比变化，处理除零错误
            def safe_percentage_change(new_val, old_val, max_cap=999):
                if pd.isna(old_val) or pd.isna(new_val):
                    return np.nan
                if old_val == 0:
                    return max_cap if new_val > 0 else 0
                return ((new_val - old_val) / old_val) * 100
            
            change_data['Beds_Change_Pct'] = change_data.apply(
                lambda row: safe_percentage_change(
                    row[f'Total Year-Round Beds (ES, TH, SH)_{selected_year}'], 
                    row[f'Total Year-Round Beds (ES, TH, SH)_{previous_year}']
                ), axis=1
            )
            
            change_data['Unsheltered_Change_Pct'] = change_data.apply(
                lambda row: safe_percentage_change(
                    row[f'Unsheltered Homeless_{selected_year}'], 
                    row[f'Unsheltered Homeless_{previous_year}']
                ), axis=1
            )
            
            # 移除无效数据
            change_data = change_data.dropna(subset=['Beds_Change_Pct', 'Unsheltered_Change_Pct'])
            
            # 步骤2: 创建分级分类
            def classify_beds_change(pct):
                if pct < 0:
                    return 'B1'  # 减少
                elif pct < 50:
                    return 'B2'  # 低/中度增长
                else:
                    return 'B3'  # 高增长
            
            def classify_unsheltered_change(pct):
                if pct > 0:
                    return 'U1'  # 增加
                elif pct > -50:
                    return 'U2'  # 轻微减少
                else:
                    return 'U3'  # 显著减少
            
            change_data['Beds_Class'] = change_data['Beds_Change_Pct'].apply(classify_beds_change)
            change_data['Unsheltered_Class'] = change_data['Unsheltered_Change_Pct'].apply(classify_unsheltered_change)
            change_data['Bivariate_Class'] = change_data['Beds_Class'] + '-' + change_data['Unsheltered_Class']
            
            # 步骤3: 定义颜色方案
            bivariate_colors = {
                'B1-U1': '#8e6d8a',  # 床位减少，无庇护者增加 - 紫色
                'B1-U2': '#a6bddb',  # 床位减少，无庇护者轻微减少 - 浅蓝
                'B1-U3': '#2b8cbe',  # 床位减少，无庇护者显著减少 - 蓝色
                'B2-U1': '#c85a5a',  # 床位低/中增长，无庇护者增加 - 红色
                'B2-U2': '#e0e0e0',  # 床位低/中增长，无庇护者轻微减少 - 灰色（稳定）
                'B2-U3': '#74c476',  # 床位低/中增长，无庇护者显著减少 - 绿色
                'B3-U1': '#ad3a3a',  # 床位高增长，无庇护者增加 - 深红（警示）
                'B3-U2': '#a1d99b',  # 床位高增长，无庇护者轻微减少 - 浅绿
                'B3-U3': '#31a354',  # 床位高增长，无庇护者显著减少 - 深绿（理想）
            }
            
            # 添加颜色到数据
            change_data['Color'] = change_data['Bivariate_Class'].map(bivariate_colors)
            
            # 创建地图
            try:
                centroids = change_data.geometry.centroid
                lats = [point.y if hasattr(point, 'y') else 39.8283 for point in centroids]
                lons = [point.x if hasattr(point, 'x') else -98.5795 for point in centroids]
            except Exception as e:
                st.warning(f"几何数据处理错误: {str(e)}")
                lats = [39.8283] * len(change_data)
                lons = [-98.5795] * len(change_data)
            
            # 创建悬停文本
            hover_text = []
            for _, row in change_data.iterrows():
                text = f"<b>{row['CoC Name']}</b><br>"
                text += f"CoC Number: {row['CoC Number']}<br>"
                text += f"State: {row['State']}<br><br>"
                text += f"<b>Bed Changes ({previous_year}-{selected_year}):</b><br>"
                text += f"{previous_year}: {row[f'Total Year-Round Beds (ES, TH, SH)_{previous_year}']:,.0f}<br>"
                text += f"{selected_year}: {row[f'Total Year-Round Beds (ES, TH, SH)_{selected_year}']:,.0f}<br>"
                text += f"Change: {row['Beds_Change_Pct']:+.1f}%<br><br>"
                text += f"<b>Unsheltered Changes ({previous_year}-{selected_year}):</b><br>"
                text += f"{previous_year}: {row[f'Unsheltered Homeless_{previous_year}']:,.0f}<br>"
                text += f"{selected_year}: {row[f'Unsheltered Homeless_{selected_year}']:,.0f}<br>"
                text += f"Change: {row['Unsheltered_Change_Pct']:+.1f}%<br><br>"
                text += f"<b>Category:</b> {row['Bivariate_Class']}"
                hover_text.append(text)
            
            # 创建图表
            fig = go.Figure()
            
            fig.add_trace(go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode='markers',
                marker=dict(
                    size=10,
                    color=change_data['Color'],
                    opacity=0.8
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                name='CoC 变化分析'
            ))
            
            fig.update_layout(
                mapbox=dict(
                    style="carto-positron",  # 使用更稳定的地图样式
                    center=dict(lat=39.8283, lon=-98.5795),
                    zoom=3.5
                ),
                height=700,
                margin=dict(l=0, r=0, t=50, b=0),
                showlegend=False,
                title=dict(
                    text=f"Bed vs Unsheltered Changes - Bivariate Map ({previous_year}→{selected_year})",
                    x=0.5,
                    y=0.98,
                    xanchor='center',
                    yanchor='top',
                    font=dict(size=18, color='#1f4e79')
                )
            )
            
            # 显示地图，添加错误处理
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception as plot_error:
                st.warning(f"Map rendering issue, trying simplified display: {str(plot_error)}")
                # Create simplified scatter plot as backup
                simple_fig = go.Figure()
                simple_fig.add_trace(go.Scatter(
                    x=lons,
                    y=lats,
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=change_data['Color'],
                        opacity=0.8
                    ),
                    text=hover_text,
                    hovertemplate='%{text}<extra></extra>',
                    name='CoC 变化分析'
                ))
                simple_fig.update_layout(
                    title=f"Bed vs Unsheltered Change Analysis ({previous_year}→{selected_year})",
                    xaxis_title="Longitude",
                    yaxis_title="Latitude",
                    height=500
                )
                st.plotly_chart(simple_fig, use_container_width=True)
            
            # 创建图例和统计信息
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("🎨 Color Legend")
                
                st.write("**Bed Change Categories:**")
                st.write("- B1: Bed decrease (<0%)")
                st.write("- B2: Bed low/moderate growth (0-50%)")
                st.write("- B3: Bed high growth (≥50%)")
                
                st.write("**Unsheltered Change Categories:**")
                st.write("- U1: Unsheltered increase (>0%)")
                st.write("- U2: Unsheltered slight decrease (-50% to 0%)")
                st.write("- U3: Unsheltered significant decrease (≤-50%)")
                
                st.write("**Color Meanings:**")
                color_meanings = [
                    ("🟣 Purple (B1-U1)", "Bed decrease, unsheltered increase"),
                    ("🔵 Light Blue (B1-U2)", "Bed decrease, unsheltered slight decrease"),
                    ("🔵 Blue (B1-U3)", "Bed decrease, unsheltered significant decrease"),
                    ("🔴 Red (B2-U1)", "Bed moderate growth, unsheltered increase"),
                    ("⚪ Gray (B2-U2)", "Bed moderate growth, unsheltered slight decrease (stable)"),
                    ("🟢 Green (B2-U3)", "Bed moderate growth, unsheltered significant decrease"),
                    ("🔴 Dark Red (B3-U1)", "Bed high growth, unsheltered increase (warning)"),
                    ("🟢 Light Green (B3-U2)", "Bed high growth, unsheltered slight decrease"),
                    ("🟢 Dark Green (B3-U3)", "Bed high growth, unsheltered significant decrease (ideal)")
                ]
                
                for color_desc, meaning in color_meanings:
                    st.write(f"- {color_desc}: {meaning}")
            
            with col2:
                st.subheader("📈 Change Statistics")
                
                # Add timestamp to verify data refresh
                from datetime import datetime
                import random
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                analysis_id = random.randint(1000, 9999)
                st.write(f"🕐 **Analysis Time:** {current_time}")
                st.write(f"📋 **Analysis ID:** BIV-{analysis_id}")
                
                # Count statistics for each category
                class_counts = change_data['Bivariate_Class'].value_counts()
                total_cocs = len(change_data)
                
                st.write(f"**Total CoC Count:** {total_cocs}")
                st.write("**Category Distribution:**")
                
                for bivariate_class in ['B1-U1', 'B1-U2', 'B1-U3', 'B2-U1', 'B2-U2', 'B2-U3', 'B3-U1', 'B3-U2', 'B3-U3']:
                    count = class_counts.get(bivariate_class, 0)
                    percentage = (count / total_cocs) * 100 if total_cocs > 0 else 0
                    color_hex = bivariate_colors[bivariate_class]
                    st.write(f"<span style='color: {color_hex}; font-weight: bold;'>●</span> {bivariate_class}: {count} ({percentage:.1f}%)", 
                            unsafe_allow_html=True)
                
                # Show average changes
                avg_beds_change = change_data['Beds_Change_Pct'].mean()
                avg_unsheltered_change = change_data['Unsheltered_Change_Pct'].mean()
                
                st.write(f"**Average Bed Change:** {avg_beds_change:+.1f}%")
                st.write(f"**Average Unsheltered Change:** {avg_unsheltered_change:+.1f}%")
                
                # Show best and concerning performing CoCs
                st.write("**Best Performance (B3-U3):**")
                best_cocs = change_data[change_data['Bivariate_Class'] == 'B3-U3']
                if len(best_cocs) > 0:
                    for _, coc in best_cocs.head(3).iterrows():
                        st.write(f"- {coc['CoC Number']} ({coc['State']})")
                else:
                    st.write("None")
                
                st.write("**Needs Attention (B1-U1, B3-U1):**")
                concern_cocs = change_data[change_data['Bivariate_Class'].isin(['B1-U1', 'B3-U1'])]
                if len(concern_cocs) > 0:
                    for _, coc in concern_cocs.head(3).iterrows():
                        st.write(f"- {coc['CoC Number']} ({coc['State']}) - {coc['Bivariate_Class']}")
                else:
                    st.write("None")
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating bivariate change map: {str(e)}")
            return None

    def create_bed_capacity_analysis(self, gdf_filtered):
        """Create bed capacity analysis chart"""
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
                
                bed_totals['State'] = state
                state_bed_data.append(bed_totals)
            
            df_beds = pd.DataFrame(state_bed_data)
            
            # Sort data
            if 'Total Year-Round Beds (ES, TH, SH)' in gdf_filtered.columns:
                sort_col = 'Total Year-Round Beds (ES, TH, SH)'
                df_beds['Total Beds'] = pd.to_numeric(gdf_filtered.groupby('State')['Total Year-Round Beds (ES, TH, SH)'].sum(), errors='coerce')
                df_beds = df_beds.sort_values('Total Beds', ascending=True)
            else:
                # If no total beds, sort by ES beds
                if 'Total Year-Round Beds (ES)' in df_beds.columns:
                    df_beds = df_beds.sort_values('Total Year-Round Beds (ES)', ascending=True)
            
            # Show only top 15 states to avoid overcrowded chart
            df_beds = df_beds.tail(15)
            
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
            
            for col in available_bed_cols:
                if col in df_beds.columns:
                    fig.add_trace(go.Bar(
                        name=bed_labels.get(col, col),
                        y=df_beds['State'],
                        x=df_beds[col],
                        orientation='h',
                        marker_color=colors.get(col, '#95A5A6'),
                        text=[f'{val:,.0f}' if val > 0 else '' for val in df_beds[col]],
                        textposition='inside',
                        textfont=dict(color='white', size=10)
                    ))
            
            # Add total homeless count as reference line (if available)
            if 'Overall Homeless' in df_beds.columns:
                fig.add_trace(go.Scatter(
                    x=df_beds['Overall Homeless'],
                    y=df_beds['State'],
                    mode='markers',
                    name='Total Homeless',
                    marker=dict(
                        symbol='diamond',
                        size=8,
                        color='orange',
                        line=dict(width=2, color='darkorange')
                    ),
                    text=[f'Homeless: {val:,.0f}' for val in df_beds['Overall Homeless']],
                    hovertemplate='%{text}<extra></extra>'
                ))
            
            fig.update_layout(
                title=dict(
                    text="State Bed Capacity Comparison Analysis (Top 15)",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=16)
                ),
                xaxis_title="Number of Beds",
                yaxis_title="State",
                barmode='stack',
                height=500,
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
            
            # Add bivariate change map 
            if selected_year > 2007:
                st.markdown("""
                <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>🔄 Annual Change Analysis Map</h3>
                """, unsafe_allow_html=True)
                bivariate_fig = self.create_bivariate_change_map(self.gdf, selected_year)
                if bivariate_fig:
                    st.markdown("---")
        
        # Trend analysis and correlation analysis
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("""
            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>📈 Time Trend Analysis</h3>
            """, unsafe_allow_html=True)
            trend_fig = self.create_trend_analysis(self.gdf, selected_states, selected_indicator)
            st.plotly_chart(trend_fig, use_container_width=True)
        
        with col4:
            st.markdown("""
            <h3 style='text-align: center; color: #1f4e79; margin: 1rem 0;'>🔗 Indicator Correlation Analysis</h3>
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