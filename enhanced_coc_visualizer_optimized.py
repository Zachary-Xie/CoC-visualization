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
            'Unsheltered Chronically Homeless Individuals'
        ]
        
        # Initialize session state for timeline controls
        if 'current_year_index' not in st.session_state:
            st.session_state.current_year_index = 0
        
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
            text += f"Unsheltered: {row['Unsheltered Homeless']:,.0f}"
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
                style="open-street-map",
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