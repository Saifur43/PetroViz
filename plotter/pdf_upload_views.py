

@login_required
def upload_drilling_report_pdf(request):
    """Handle PDF upload for drilling reports and extract data."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'error': 'No PDF file uploaded'}, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file type
    if not pdf_file.name.endswith('.pdf'):
        return JsonResponse({'error': 'File must be a PDF'}, status=400)
    
    try:
        from .utils.pdf_parser import parse_drilling_report_pdf
        
        # Parse the PDF
        data = parse_drilling_report_pdf(pdf_file)
        
        return JsonResponse({
            'success': True,
            'data': data,
            'message': 'PDF parsed successfully'
        })
    except ImportError:
        return JsonResponse({
            'error': 'pdfplumber library not installed. Please install it with: pip install pdfplumber'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error parsing PDF: {str(e)}'
        }, status=500)


@login_required
def upload_lithology_pdf(request):
    """Handle PDF upload for lithology data and extract structured information."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'error': 'No PDF file uploaded'}, status=400)
    
    pdf_file = request.FILES['pdf_file']
    
    # Validate file type
    if not pdf_file.name.endswith('.pdf'):
        return JsonResponse({'error': 'File must be a PDF'}, status=400)
    
    try:
        from .utils.pdf_parser import parse_lithology_pdf
        
        # Parse the PDF
        lithology_entries = parse_lithology_pdf(pdf_file)
        
        if not lithology_entries:
            return JsonResponse({
                'error': 'No lithology data found in PDF. Please check the PDF format.'
            }, status=400)
        
        # Return the first entry (or you could return all entries)
        # For now, we'll return the first one to populate the form
        data = lithology_entries[0] if lithology_entries else {}
        
        return JsonResponse({
            'success': True,
            'data': data,
            'total_entries': len(lithology_entries),
            'message': f'PDF parsed successfully. Found {len(lithology_entries)} lithology interval(s).'
        })
    except ImportError:
        return JsonResponse({
            'error': 'pdfplumber library not installed. Please install it with: pip install pdfplumber'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error parsing PDF: {str(e)}'
        }, status=500)
