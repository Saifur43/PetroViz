# PetroVis - Petroleum Data Visualization and Management System

PetroVis is a comprehensive Django-based web application designed for managing and visualizing petroleum exploration and production data. The system provides tools for handling well data, core analysis, drilling reports, and production metrics in the petroleum industry.

## Features

- **Core Sample Data Management**
  - Store and visualize core sample data
  - Upload and manage core images and lithology images
  - Track core properties including porosity, permeability, and grain density

- **Well Data Analysis**
  - Comprehensive well information tracking
  - Drilling report management
  - Integration with production data
  - Exploration timeline visualization

- **Production Data Visualization**
  - Interactive graphs and charts
  - Production metrics tracking
  - Gas field production analysis

- **Drilling Operations**
  - Daily drilling report management
  - Operation activity tracking
  - Real-time drilling parameters monitoring
  - Lithology composition analysis

- **Exploration Timeline**
  - Visual representation of exploration activities
  - Category-based exploration tracking
  - Interactive timeline interface

## Technology Stack

- **Backend Framework**: Django 5.0.2
- **Database**: SQLite3 (default)
- **Frontend**: 
  - Bootstrap 5 (via crispy-bootstrap5)
  - JavaScript for interactive visualizations
- **Data Processing**:
  - NumPy
  - Pandas
  - Matplotlib for data visualization
  - Lasio for well log data processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Saifur43/PetroViz.git
cd PetroViz
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Run database migrations:
```bash
python manage.py migrate
```

5. Create a superuser (admin):
```bash
python manage.py createsuperuser
```

6. Start the development server:
```bash
python manage.py runserver
```

## Data Population

The system includes management commands for populating different types of data:

- `python manage.py populate_data` - Populate basic well data
- `python manage.py populate_drilling_report` - Add drilling reports
- `python manage.py populate_lithology` - Import lithology data
- `python manage.py populate_operations` - Add operation activities

## Project Structure

- `PetroVis/` - Main project configuration
- `plotter/` - Main application directory
  - `management/commands/` - Custom management commands
  - `templates/` - HTML templates
  - `models.py` - Database models
  - `views.py` - View logic
  - `urls.py` - URL routing

## Data Models

- `Core` - Manages core sample data and images
- `WellData` - Stores well-specific information
- `ProductionData` - Tracks production metrics
- `DailyDrillingReport` - Records drilling operations
- `ExplorationTimeline` - Manages exploration activities
- `ExplorationCategory` - Categorizes exploration activities
- `OperationActivity` - Tracks operational activities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django community for the excellent web framework
- Contributors to the scientific Python stack
- All contributors to this project

## Contact

Project Link: https://github.com/Saifur43/PetroViz