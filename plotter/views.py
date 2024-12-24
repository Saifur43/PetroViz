import pandas as pd
import matplotlib.pyplot as plt
from django.shortcuts import render, redirect
from .models import WellData, Core
from .forms import CSVUploadForm
from io import BytesIO
import base64
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
from io import BytesIO
from django.shortcuts import render
from .models import WellData, Core

from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
import os

def upload_csv(request):
    message = None  # To store success or error messages
    error_rows = []  # To track rows with errors
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # image_files = request.FILES.getlist('image_files')  # You can remove this line for now

            try:
                # Attempt to read the uploaded file as a DataFrame
                df = pd.read_csv(file)

                # Validate required columns
                required_columns = ['Well Name', 'Core No', 
                                    'Length', 'Depth', 'Porosity', 'Perm Kair(mD)', 
                                    'Grain Density', 'Resistivity']
                missing_columns = [col for col in required_columns if col not in df.columns]

                if missing_columns:
                    raise ValueError(f"The uploaded file is missing the following required columns: {', '.join(missing_columns)}")

                # Save each row to the database, skipping rows with errors
                for index, row in df.iterrows():
                    try:
                        # For now, image is set to None (null)
                        core, created = Core.objects.get_or_create(
                            core_no=row['Core No'],
                        )

                        # No image upload for now, image remains null
                        # If you decide to upload images later, you can update the Core record

                        # Create WellData object
                        well_data = WellData.objects.create(
                            well_name=row['Well Name'],
                            core_no=row['Core No'],
                            core=core,  # Link the WellData to the Core
                            length=row.get('Length', None),
                            depth=row.get('Depth', None),
                            porosity=row.get('Porosity', None),
                            perm_kair=row.get('Perm Kair(mD)', None),
                            grain_density=row.get('Grain Density', None),
                            resistivity=row.get('Resistivity', None),
                        )

                    except Exception as e:
                        # Log the index and error for this row
                        error_rows.append((index + 1, str(e)))

                # Generate a message based on the outcome
                if error_rows:
                    message = f"Data uploaded with {len(error_rows)} row(s) skipped due to errors."
                else:
                    message = "Data uploaded successfully!"

            except ValueError as e:
                message = f"Error: {str(e)}"
            except pd.errors.ParserError:
                message = "Error: The file could not be parsed as a CSV. Please upload a valid CSV file."
            except Exception as e:
                message = f"An unexpected error occurred: {str(e)}"
    else:
        form = CSVUploadForm()

    return render(request, 'visualization/upload.html', {'form': form, 'message': message, 'error_rows': error_rows})


from django.shortcuts import render
from .models import Core, WellData
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
import io
import base64
import numpy as np

def visualize_data(request):
    selected_well = request.GET.get('well_name')
    selected_core = request.GET.get('core_no')

    # Fetch core numbers filtered by the selected well
    core_numbers = (
        WellData.objects.filter(well_name=selected_well)
        .values_list('core_no', flat=True)
        .distinct()
        if selected_well
        else Core.objects.values_list('core_no', flat=True)
    )

    if selected_well and selected_core:
        core = Core.objects.get(core_no=selected_core)
        well_data = WellData.objects.filter(well_name=selected_well, core_no=selected_core)

        # Prepare data for plotting
        data = well_data.values('depth', 'porosity', 'perm_kair')
        df = pd.DataFrame(list(data))

        # Create figure for the plot
        fig, (ax_img, ax_plot) = plt.subplots(1, 2, figsize=(8, 12), gridspec_kw={'width_ratios': [1, 3]})
        core_img_url = core.image.url if core.image else None

        # Plot the core image
        if core_img_url:
            core_img = mpimg.imread(core.image.path)
            depth_min, depth_max = df['depth'].min(), df['depth'].max()
            depth_padding = (depth_max - depth_min) * 0.05

            ax_img.imshow(core_img, aspect='auto', extent=[0, 1, depth_max + depth_padding, depth_min - depth_padding])
            ax_img.set_title("Core Image")
            ax_img.set_xlabel("Core")
            ax_img.set_ylabel("Depth (m)")
            ax_img.set_xticks([])
            ax_img.set_ylim(depth_max + depth_padding, depth_min - depth_padding)
            ax_img.grid(False)

        # Plot porosity and permeability with dual scales
        ax_perm = ax_plot.twiny()  # Create a secondary x-axis

        # Plot porosity
        ax_plot.scatter(df['porosity'], df['depth'], color='red', label='Porosity', s=20)
        ax_plot.set_xlabel('Porosity (%)', color='red')
        ax_plot.tick_params(axis='x', colors='red')
        ax_plot.set_xlim(df['porosity'].min() * 0.9, df['porosity'].max() * 1.1)

        # Plot permeability on the secondary axis
        ax_perm.scatter(df['perm_kair'], df['depth'], color='blue', label='Permeability', s=20)
        ax_perm.set_xlabel('Permeability (mD)', color='blue')
        ax_perm.tick_params(axis='x', colors='blue')
        ax_perm.set_xscale('log')
        ax_perm.set_xlim(df['perm_kair'].min() * 0.9, df['perm_kair'].max() * 1.1)

        # Add black line traces
        n_points = len(df)
        if n_points > 1:
            perm_line = df['porosity'] * np.random.lognormal(0, 0.1, n_points)
            ax_plot.plot(perm_line, df['depth'], 'k-', alpha=0.5, linewidth=0.5, label='Porosity Trace')

            perm_kair_line = df['perm_kair'] * np.random.lognormal(0, 0.1, n_points)
            ax_perm.plot(perm_kair_line, df['depth'], 'k-', alpha=0.5, linewidth=0.5, label='Permeability Trace')

        # Common settings
        ax_plot.set_ylim(depth_max + depth_padding, depth_min - depth_padding)
        ax_plot.set_title('Core Properties')
        ax_plot.legend(loc='upper right')

        plt.tight_layout()

        # Save plot to a BytesIO object
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plot_url = base64.b64encode(buf.read()).decode('utf-8')

        return render(request, 'visualization/visualize_data.html', {
            'selected_well': selected_well,
            'selected_core': selected_core,
            'plot_url': plot_url,
            'core_img_url': core_img_url,
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
        })

    else:
        return render(request, 'visualization/visualize_data.html', {
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
            'selected_well': selected_well,
            'selected_core': selected_core
        })



def graph_view(request):
    selected_well = request.GET.get('well_name')
    selected_core = request.GET.get('core_no')

    # Fetch core numbers filtered by the selected well
    core_numbers = (
        WellData.objects.filter(well_name=selected_well)
        .values_list('core_no', flat=True)
        .distinct()
        if selected_well
        else Core.objects.values_list('core_no', flat=True)
    )

    if selected_well and selected_core:
        # Fetch the core and well data
        core = Core.objects.get(core_no=selected_core)
        well_data = WellData.objects.filter(
            well_name=selected_well, 
            core_no=selected_core
        ).values('depth', 'porosity', 'perm_kair')
        
        # Convert to list for JSON serialization
        data_list = list(well_data)
        
        # Prepare data for the template
        context = {
            'selected_well': selected_well,
            'selected_core': selected_core,
            'core_img_url': core.image.url if core.image else None,
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
            'chart_data': {
                'depths': [d['depth'] for d in data_list],
                'porosity': [d['porosity'] for d in data_list],
                'permeability': [d['perm_kair'] for d in data_list]
            }
        }
    else:
        context = {
            'well_names': WellData.objects.values_list('well_name', flat=True).distinct(),
            'core_numbers': core_numbers,
            'selected_well': selected_well,
            'selected_core': selected_core
        }

    return render(request, 'visualization/graph.html', context)