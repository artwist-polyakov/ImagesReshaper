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
                throw new Error('Ошибка загрузки');
            }
            
            const result = await response.json();
            if (result.status === 'success') {
                alert('Файл успешно загружен! Проверьте сообщения в боте.');
            } else {
                alert('Произошла ошибка при загрузке файла');
            }
            
        } catch (error) {
            console.error('Ошибка:', error);
            alert('Произошла ошибка при загрузке файла');
        }
    }
}); 