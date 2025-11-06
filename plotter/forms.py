from django import forms
from .models import BHA, BHAComponent, BHAComponentPosition

class CSVUploadForm(forms.Form):
    file = forms.FileField()

class BHAComponentForm(forms.ModelForm):
    class Meta:
        model = BHAComponent
        fields = ['name', 'type', 'connection_type', 'svg_template', 'description']
        widgets = {
            'svg_template': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter SVG template with placeholders: {length}, {outer_diameter}, {inner_diameter}, {scale_factor}'
            }),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        return super().clean()

class BHAForm(forms.ModelForm):
    class Meta:
        model = BHA
        fields = ['name', 'drilling_report', 'notes', 'is_active']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        drilling_report = cleaned_data.get('drilling_report')
        
        # Check if there's already an active BHA for this drilling report
        if cleaned_data.get('is_active'):
            existing_active = BHA.objects.filter(
                drilling_report=drilling_report,
                is_active=True
            ).exclude(id=self.instance.id if self.instance else None).exists()
            
            if existing_active:
                raise forms.ValidationError(
                    "There is already an active BHA for this drilling report. "
                    "Please deactivate it first."
                )
        return cleaned_data

class BHAComponentPositionForm(forms.ModelForm):
    class Meta:
        model = BHAComponentPosition
        fields = ['component', 'position', 'distance_from_bit', 'length', 'outer_diameter', 'inner_diameter', 'weight']
        widgets = {
            'distance_from_bit': forms.NumberInput(attrs={'step': '0.01'}),
            'length': forms.NumberInput(attrs={'step': '0.01'}),
            'outer_diameter': forms.NumberInput(attrs={'step': '0.01'}),
            'inner_diameter': forms.NumberInput(attrs={'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.bha:
            # Filter components based on compatibility with the last component
            last_position = self.instance.bha.component_positions.order_by('-position').first()
            if last_position:
                compatible_components = []
                for component in BHAComponent.objects.all():
                    is_compatible, _ = component.validate_connection_compatibility(last_position.component)
                    if is_compatible:
                        compatible_components.append(component.id)
                self.fields['component'].queryset = BHAComponent.objects.filter(id__in=compatible_components)

    def clean(self):
        cleaned_data = super().clean()
        position = cleaned_data.get('position')
        distance_from_bit = cleaned_data.get('distance_from_bit')
        length = cleaned_data.get('length')
        od = cleaned_data.get('outer_diameter')
        id_ = cleaned_data.get('inner_diameter')

        if self.instance and self.instance.bha:
            # Validate position number is unique in this BHA
            existing = self.instance.bha.component_positions.filter(position=position)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"Position {position} is already taken in this BHA")

            # Validate distance is greater than previous component
            if position > 1:
                prev_position = self.instance.bha.component_positions.filter(
                    position=position-1
                ).first()
                if prev_position and distance_from_bit <= prev_position.distance_from_bit:
                    raise forms.ValidationError(
                        "Distance from bit must be greater than the previous component's distance"
                    )

        # Generic input validations
        if length is not None and length <= 0:
            raise forms.ValidationError("Length must be greater than 0")
        if od is not None and od <= 0:
            raise forms.ValidationError("Outer diameter must be greater than 0")
        if id_ is not None and id_ < 0:
            raise forms.ValidationError("Inner diameter cannot be negative")
        if id_ is not None and od is not None and id_ >= od:
            raise forms.ValidationError("Inner diameter must be less than outer diameter")

        return cleaned_data
