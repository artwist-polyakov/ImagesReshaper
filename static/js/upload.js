document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImage = document.getElementById('previewImage');
    const processButton = document.getElementById('processButton');
    const deleteButton = document.getElementById('deleteButton');
    const uploadNewButton = document.getElementById('uploadNewButton');
    
    const cropArea = document.querySelector('.crop-area');
    const cropContainer = document.querySelector('.crop-container');
    let currentFile = null;
    
    // Параметры для кропа
    const minSize = 50; // Минимальный размер области кропа
    let activeHandle = null;
    let startX, startY;
    let startLeft, startTop, startWidth, startHeight;

    // Инициализация перетаскивания
    document.querySelectorAll('.crop-handle').forEach(handle => {
        handle.addEventListener('mousedown', startResize);
    });

    function startResize(e) {
        e.preventDefault();
        activeHandle = e.target.dataset.handle;
        
        const rect = cropArea.getBoundingClientRect();
        startX = e.clientX;
        startY = e.clientY;
        startLeft = rect.left;
        startTop = rect.top;
        startWidth = rect.width;
        startHeight = rect.height;

        document.addEventListener('mousemove', resize);
        document.addEventListener('mouseup', stopResize);
    }

    function resize(e) {
        if (!activeHandle) return;

        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        const containerRect = cropContainer.getBoundingClientRect();
        const imageRect = previewImage.getBoundingClientRect();

        let newLeft = startLeft - containerRect.left;
        let newTop = startTop - containerRect.top;
        let newWidth = startWidth;
        let newHeight = startHeight;

        switch (activeHandle) {
            case 'nw':
                newLeft = Math.max(0, Math.min(newLeft + deltaX, startLeft + startWidth - containerRect.left - minSize));
                newTop = Math.max(0, Math.min(newTop + deltaY, startTop + startHeight - containerRect.top - minSize));
                newWidth = startWidth - (newLeft - (startLeft - containerRect.left));
                newHeight = startHeight - (newTop - (startTop - containerRect.top));
                break;
            case 'ne':
                newTop = Math.max(0, Math.min(newTop + deltaY, startTop + startHeight - containerRect.top - minSize));
                newWidth = Math.min(imageRect.width - newLeft, Math.max(minSize, startWidth + deltaX));
                newHeight = startHeight - (newTop - (startTop - containerRect.top));
                break;
            case 'sw':
                newLeft = Math.max(0, Math.min(newLeft + deltaX, startLeft + startWidth - containerRect.left - minSize));
                newWidth = startWidth - (newLeft - (startLeft - containerRect.left));
                newHeight = Math.min(imageRect.height - newTop, Math.max(minSize, startHeight + deltaY));
                break;
            case 'se':
                newWidth = Math.min(imageRect.width - newLeft, Math.max(minSize, startWidth + deltaX));
                newHeight = Math.min(imageRect.height - newTop, Math.max(minSize, startHeight + deltaY));
                break;
        }

        // Проверяем, чтобы размеры не стали отрицательными
        if (newWidth > minSize && newHeight > minSize) {
            cropArea.style.left = `${newLeft}px`;
            cropArea.style.top = `${newTop}px`;
            cropArea.style.width = `${newWidth}px`;
            cropArea.style.height = `${newHeight}px`;
        }
    }

    function stopResize() {
        activeHandle = null;
        document.removeEventListener('mousemove', resize);
        document.removeEventListener('mouseup', stopResize);
    }

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

    // Обработчики событий для кнопок
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
                
                // Инициализируем кроп после загрузки изображения
                previewImage.onload = function() {
                    initCrop();
                };
            };
            reader.readAsDataURL(file);
        }
    }

    function initCrop() {
        const imageRect = previewImage.getBoundingClientRect();
        const containerRect = cropContainer.getBoundingClientRect();
        
        // Устанавливаем размеры и позицию кропа равными размерам изображения
        cropArea.style.left = '0';
        cropArea.style.top = '0';
        cropArea.style.width = imageRect.width + 'px';
        cropArea.style.height = imageRect.height + 'px';
    }

    async function handleFileUpload(file) {
        try {
            processButton.disabled = true;
            processButton.textContent = 'Обработка...';

            // Создаем canvas для кропа
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            // Получаем координаты кропа
            const cropRect = cropArea.getBoundingClientRect();
            const imageRect = previewImage.getBoundingClientRect();

            // Вычисляем координаты кропа относительно изображения
            const x = (cropRect.left - imageRect.left);
            const y = (cropRect.top - imageRect.top);
            const width = cropRect.width;
            const height = cropRect.height;

            // Создаем временное изображение для получения реальных размеров
            const img = new Image();
            img.src = previewImage.src;
            
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });

            // Вычисляем масштаб между реальным изображением и отображаемым
            const scaleX = img.naturalWidth / imageRect.width;
            const scaleY = img.naturalHeight / imageRect.height;

            // Устанавливаем размеры canvas равными размеру кропа в реальных пикселях
            canvas.width = width * scaleX;
            canvas.height = height * scaleY;

            // Выполняем кроп с сохранением оригинального качества
            ctx.drawImage(
                img,
                x * scaleX,
                y * scaleY,
                width * scaleX,
                height * scaleY,
                0,
                0,
                canvas.width,
                canvas.height
            );

            // Конвертируем canvas в blob без дополнительного сжатия
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 1.0);  // Качество 1.0 - максимальное
            });

            const formData = new FormData();
            formData.append('file', blob, 'cropped.jpg');

            // Получаем токен из URL
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get('token');

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