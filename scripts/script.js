$(document).ready(function(){
    $('.increment-btn').click(function (e){
        e.preventDefault();

        // Get the current quantity value from the input field
        var quantityInput = $(this).siblings('.product_quantity');
        var quantity = parseInt(quantityInput.val());

        // Increment the quantity
        quantity += 1;

        // Update the input value with the new quantity
        quantityInput.val(quantity);
    });

    $('.decrement-btn').click(function (e){
        e.preventDefault();

        // Get the current quantity value from the input field
        var quantityInput = $(this).siblings('.product_quantity');
        var quantity = parseInt(quantityInput.val());

        // Decrement the quantity
        if (quantity > 1) {
            quantity -= 1;
        }

        // Update the input value with the new quantity
        quantityInput.val(quantity);
    });
});
