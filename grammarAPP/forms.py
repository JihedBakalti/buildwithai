from django import forms

class GrammarCheckForm(forms.Form):
    text_input = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Paste your text here to check grammar...',
            'rows': 10,
            'id': 'text-input'
        }),
        required=False,
        label='Text Input',
        help_text='Enter your text directly or upload a file below'
    )
    
    file_upload = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.txt',
            'id': 'file-upload'
        }),
        required=False,
        label='Upload Text File',
        help_text='Upload a .txt file (optional if you enter text above)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        text_input = cleaned_data.get('text_input', '')
        if text_input:
            text_input = text_input.strip()
        file_upload = cleaned_data.get('file_upload')
        
        if not text_input and not file_upload:
            raise forms.ValidationError(
                "Please either enter text in the text area or upload a .txt file."
            )
        
        if file_upload:
            # Check file extension
            if not file_upload.name.endswith('.txt'):
                raise forms.ValidationError("Please upload a .txt file only.")
            
            # Check file size (max 1MB)
            if file_upload.size > 1024 * 1024:
                raise forms.ValidationError("File size should not exceed 1MB.")
            
            # Read file content
            try:
                file_content = file_upload.read().decode('utf-8')
                cleaned_data['file_content'] = file_content
            except UnicodeDecodeError:
                raise forms.ValidationError("File must be a valid UTF-8 text file.")
        
        return cleaned_data
    
    def get_text(self):
        """Get the text to check from either input or file"""
        text_input = self.cleaned_data.get('text_input', '').strip()
        file_content = self.cleaned_data.get('file_content', '')
        
        if text_input:
            return text_input
        elif file_content:
            return file_content
        return ''

