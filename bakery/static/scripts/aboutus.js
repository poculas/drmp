let nextBtn = document.querySelector('.next');
let prevBtn = document.querySelector('.prev');
let slider = document.querySelector('.slider');
let sliderList = slider.querySelector('.slider .list');
let thumbnail = document.querySelector('.slider .thumbnail');
let thumbnailItems = thumbnail.querySelectorAll('.item');

thumbnail.appendChild(thumbnailItems[0]);

nextBtn.onclick = function() {
    moveSlider('next');
}

prevBtn.onclick = function() {
    moveSlider('prev');
}
function moveSlider(direction) {
    let sliderItems = sliderList.querySelectorAll('.item');
    let thumbnailItems = thumbnail.querySelectorAll('.item');

    // Hide all main slider items before moving
    sliderItems.forEach(item => item.style.display = 'none');

    if(direction === 'next'){
        sliderList.appendChild(sliderItems[0]); // Move the first item to the end
        slider.classList.add('next');
        
        // Move the first thumbnail to the end (without hiding them)
        thumbnail.appendChild(thumbnailItems[0]);

    } else {
        sliderList.prepend(sliderItems[sliderItems.length - 1]); // Move the last item to the front
        slider.classList.add('prev');

        // Move the last thumbnail to the front (without hiding them)
        thumbnail.prepend(thumbnailItems[thumbnailItems.length - 1]);
    }

    // Show the first slider item after moving
    sliderList.querySelector('.item:first-child').style.display = 'block';

    // Add animation end handler to remove classes after animation
    slider.addEventListener('animationend', function() {
        if(direction === 'next'){
            slider.classList.remove('next');
        } else {
            slider.classList.remove('prev');
        }
    }, {once: true});
}