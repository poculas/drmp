function showNotification(message, type = 'success', position = 'top-right') {
    const existingNotification = document.querySelector('.notification-popup');
    if (existingNotification) {
        existingNotification.remove();
    }

    const notification = document.createElement('div');
    notification.className = 'notification-popup';
    notification.textContent = message;

    let bgColor = '#28a745';
    if (type === 'error') {
        bgColor = '#dc3545';
    } else if (type === 'warning') {
        bgColor = '#ffc107';
    } else if (type === 'info') {
        bgColor = '#17a2b8';
    }

    notification.style.backgroundColor = bgColor;
    notification.setAttribute('data-position', position);

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 6000);
}

function showNotificationAfterElement(message, type, elementSelector) {
    const element = document.querySelector(elementSelector);
    if (!element) {
        showNotification(message, type);
        return;
    }

    const existingNotification = document.querySelector('.notification-popup');
    if (existingNotification) {
        existingNotification.remove();
    }

    const notification = document.createElement('div');
    notification.className = 'notification-popup notification-inline';
    notification.textContent = message;

    let bgColor = '#28a745';
    if (type === 'error') {
        bgColor = '#dc3545';
    } else if (type === 'warning') {
        bgColor = '#ffc107';
    } else if (type === 'info') {
        bgColor = '#17a2b8';
    }

    notification.style.backgroundColor = bgColor;

    element.parentNode.insertBefore(notification, element.nextSibling);

    setTimeout(() => {
        notification.remove();
    }, 6000);
}
