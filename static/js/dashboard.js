document.addEventListener("DOMContentLoaded", () => {
    const cards = document.querySelectorAll(".product-card");

    cards.forEach((card, i) => {
        card.style.opacity = 0;
        card.style.transform = "translateY(30px)";
        setTimeout(() => {
            card.style.transition = "0.5s ease";
            card.style.opacity = 1;
            card.style.transform = "translateY(0)";
        }, i * 120);
    });
});

 
document.getElementById('add-spec-btn').onclick = function () {
    const container = document.getElementById('spec-container');

    const row = document.createElement('div');
    row.className = 'row mb-2 spec-row';

    row.innerHTML = `
        <div class="col">
            <input type="text" name="spec_key[]" class="form-control" placeholder="Tên thông số">
        </div>
        <div class="col">
            <input type="text" name="spec_value[]" class="form-control" placeholder="Giá trị">
        </div>
        <div class="col-auto">
            <button type="button" class="btn btn-danger remove-spec">✖</button>
        </div>
    `;

    container.appendChild(row);
};

document.addEventListener('click', function (e) {
    if (e.target.classList.contains('remove-spec')) {
        e.target.closest('.spec-row').remove();
    }
});
