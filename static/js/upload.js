document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
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
            handleFileUpload(files[0]);
        }
    });
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    }
    
    async function handleFileUpload(file) {
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
        
        const formData = new FormData();
        formData.append('file', file);
        
        // Получаем токен из URL
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        
        try {
            const response = await fetch(`/upload?token=${token}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка загрузки');
            }
            
            // Получаем blob из ответа
            const blob = await response.blob();
            
            // Создаем ссылку для скачивания
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'processed_image.jpg';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            alert('Файл успешно обработан!');
            
        } catch (error) {
            console.error('Ошибка:', error);
            alert(error.message || 'Произошла ошибка при загрузке файла');
        }
    }
}); 