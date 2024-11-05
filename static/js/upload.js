document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImage = document.getElementById('previewImage');
    const processButton = document.getElementById('processButton');
    const deleteButton = document.getElementById('deleteButton');
    const uploadNewButton = document.getElementById('uploadNewButton');
    
    let currentFile = null;

    // Обработка клика по зоне загрузки
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Обработка выбора файла
    fileInput.addEventListener('change', handleFileSelect);
    
    // Обработка drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#000';
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#ccc';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#ccc';
        
        const files = e.dataTransfer.files;
        if (files.length) {
            handleFileSelect({ target: { files: files } });
        }
    });

    processButton.addEventListener('click', () => {
        if (currentFile) {
            handleFileUpload(currentFile);
        }
    });

    deleteButton.addEventListener('click', () => {
        resetUpload();
    });

    uploadNewButton.addEventListener('click', () => {
        resetUpload();
        fileInput.click();
    });

    function resetUpload() {
        currentFile = null;
        fileInput.value = '';
        imagePreview.style.display = 'none';
        dropZone.style.display = 'block';
    }
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            // Проверка размера файла
            const maxSize = 52428800; // 50MB
            if (file.size > maxSize) {
                alert('Файл слишком большой. Максимальный размер: 50MB');
                return;
            }
            
            // Проверка типа файла
            if (!file.type.startsWith('image/')) {
                alert('Пожалуйста, загрузите изображение');
                return;
            }

            currentFile = file;
            
            // Показываем предпросмотр
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                dropZone.style.display = 'none';
                imagePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }
    
    async function handleFileUpload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        // Получаем токен из URL
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        
        try {
            processButton.disabled = true;
            processButton.textContent = 'Обработка...';
            
            const response = await fetch(`/upload?token=${token}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка загрузки');
            }
            
            alert('Изображение успешно отправлено в Telegram!');
            resetUpload();
            
        } catch (error) {
            console.error('Ошибка:', error);
            alert(error.message || 'Произошла ошибка при загрузке файла');
        } finally {
            processButton.disabled = false;
            processButton.textContent = 'Обработать';
        }
    }
}); 