import re
import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(layout="wide", page_title="Scottish SOTA Summit Explorer")


# Load data
@st.cache_data
def load_data():
    df = pd.read_excel("rhb-gm-summits.xlsx", sheet_name="byregion")
    df['Original Region'] = df['SOTA Ref'].str.extract(r'GM/([A-Z]+)-')
    return df

df = load_data()

def extract_sota_region(sota_ref):
    # Extract the two letters after the slash, e.g. GM/SS-001 → SS
    match = re.search(r"/([A-Z]{2})-", sota_ref)
    return match.group(1) if match else ""

df['Original SOTA region'] = df['SOTA Ref'].apply(extract_sota_region)


# Sidebar – Region assignment
st.sidebar.header("Region Reassignment")
colour_by = st.sidebar.selectbox("Colour markers by:", ["Area", "New gm region"])

# Region assignment by Area
sota_regions = ['SS', 'ES', 'CS', 'SI', 'WS', 'NS']
area_list = sorted(df['Area'].dropna().unique())
area_to_region = {}

st.sidebar.markdown("### Assign SOTA region to each Area:")
# Create a mapping from Area code to Area name
area_name_map = df.set_index('Area')['Area name'].to_dict()

for area in area_list:
    area_name = area_name_map.get(area, area)  # fallback to code if name missing
    default = df[df['Area'] == area]['New gm region'].mode()
    default_value = default.iat[0] if not default.empty and default.iat[0] in sota_regions else 'SS'
    label = f"{area_name} ({area})"
    region = st.sidebar.selectbox(label, sota_regions, index=sota_regions.index(default_value), key=area)
    area_to_region[area] = region

# Apply region assignments
df['Assigned Region'] = df['Area'].map(area_to_region)

# Colour mapping (shared for both maps)
def make_color_map(values):
    unique = sorted(values.dropna().unique())
    cmap = plt.get_cmap("Set1", len(unique))
    return {val: [int(c * 255) for c in cmap(i)[:3]] for i, val in enumerate(unique)}

# Compute shared colour map
combined_categories = pd.concat([df['Original Region'], df['Assigned Region'], df[colour_by]]).dropna().unique()
color_map = make_color_map(pd.Series(combined_categories))

# Assign RGB colors to each row
df['Color'] = df[colour_by].map(color_map)
df['Original Color'] = df['Original Region'].map(color_map)

# Page title
st.title("Scottish SOTA Summit Reassignment Explorer")

deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/outdoors-v12",
    initial_view_state=pdk.ViewState(
        latitude=df['Latitude'].mean(),
        longitude=df['Longitude'].mean(),
        zoom=6.2,
        pitch=0,
    ),
    layers=[
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position='[Longitude, Latitude]',
            get_fill_color='Color',
            get_radius=1000,
            pickable=True,
            stroked=True,
            get_line_color=[0, 0, 0],
            line_width_min_pixels=1,
            opacity=0.9,
        )
    ],
    tooltip={
        "html": (
            "<b>{Hill name}</b><br/>"
            "Area: {Area}<br/>"
            "New gm region: {Assigned Region}<br/>"
            "Original SOTA region: {Original SOTA region}"
        )
    }
)

# Height is set here
st.pydeck_chart(deck, use_container_width=True, height=900)

# Comparison bar chart
st.subheader("📊 Region Assignment Comparison")

original_counts = df['Original Region'].value_counts().rename("Original")
assigned_counts = df['Assigned Region'].value_counts().rename("New")
comparison_df = pd.concat([original_counts, assigned_counts], axis=1).fillna(0).astype(int)
st.dataframe(comparison_df)

fig = px.bar(
    comparison_df.reset_index().melt(id_vars='index'),
    x='index',
    y='value',
    color='variable',
    labels={'index': 'Region', 'value': 'Summit Count'},
    barmode='group',
    title="Summit Counts by Region: Original vs Assigned"
)
st.plotly_chart(fig)

# Update the New gm region column based on sidebar selections
df['New gm region'] = df['Area'].map(area_to_region)

# Download button
csv = df.to_csv(index=False)
st.download_button(
    label="Download updated regions CSV",
    data=csv,
    file_name="rhb-gm-summits-updated.csv",
    mime="text/csv",
)

# Recalculate if needed
original = df.groupby(['Original SOTA region', 'Points']).size().unstack(fill_value=0)
new = df.groupby(['New gm region', 'Points']).size().unstack(fill_value=0)

original.index = [f"{r} (original)" for r in original.index]
new.index = [f"{r} (new)" for r in new.index]

# Combine
combined = pd.concat([original, new])

# Build desired order: interleave original and new
regions = sorted(set(df['Original SOTA region'].dropna()))
ordered_index = []
for r in regions:
    if f"{r} (original)" in combined.index:
        ordered_index.append(f"{r} (original)")
    if f"{r} (new)" in combined.index:
        ordered_index.append(f"{r} (new)")

# Normalize to proportions
percent_df = combined.loc[ordered_index].div(combined.loc[ordered_index].sum(axis=1), axis=0)

# Plot
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 6))
percent_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab10')

ax.set_title("Proportional Summit Distribution by Region (Original vs New)")
ax.set_ylabel("Proportion")
ax.set_xlabel("Region")
ax.legend(title='Points', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

st.pyplot(fig)





