document.addEventListener("DOMContentLoaded", function () {
    const togglePassword = document.getElementById("togglePassword");
    const passwordField = document.getElementById("pass");
    const retogglePassword = document.getElementById("retogglePassword");
    const retypepasswordField = document.getElementById("retype");

    togglePassword.addEventListener("click", function () {
        const type = passwordField.getAttribute("type") === "password" ? "text" : "password";
        passwordField.setAttribute("type", type);
        this.classList.toggle("fa-eye-slash");
        this.classList.toggle("fa-eye");
    });

    retogglePassword.addEventListener("click", function () {
        const type = retypepasswordField.getAttribute("type") === "password" ? "text" : "password";
        retypepasswordField.setAttribute("type", type);
        this.classList.toggle("fa-eye-slash");
        this.classList.toggle("fa-eye");
    });

    document.getElementById("registrationForm").addEventListener("submit", async function(event) {
        event.preventDefault();

        const formData = new FormData(this);
        const data = {};
        formData.forEach((value, key) => data[key] = value);

        if (validateForm(data)) {
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (response.ok) {
                    window.location.href = '/login';
                } else {
                    displayError(result.message);
                }
            } catch (error) {
                displayError("An unexpected error occurred");
            }
        }
    });

    function validateForm(data) {
        const namePattern = /^[A-Za-z\s]+$/;
        const phonePattern = /^\d{10}$/;
        const regPattern = /^([A-Z]{2})[ -][0-9]{1,2}(?: [A-Z])?(?: [A-Z]*)? [0-9]{4}$/;
        const passPattern = /^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%#?&]).{6,}$/;
        const makePattern = /^(19|20)\d{2}$/;
        const emailPattern = /^[a-zA-Z0-9._]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

        if (!namePattern.test(data.name)) {
            displayError("Please enter a valid name with only alphabets.");
            return false;
        }

        if (!phonePattern.test(data.phone)) {
            displayError("Please enter a valid 10-digit phone number.");
            return false;
        }
        if (!emailPattern.test(data.email)) {
            displayError("Please enter a valid email address");
            return false;
        }

        if (!regPattern.test(data.reg)) {
            displayError("Please enter a valid vehicle registration number \n For example: KA XX ET XXXX or KL-XX-CR-XXXX.");
            return false;
        }

        if (!passPattern.test(data.pass)) {
            displayError("Password must contain at least one captial letter, one number, and one special character.");
            return false;
        }

        if (data.pass !== data.retype) {
            displayError("Passwords do not match.");
            return false;
        }

        if (data.model === "") {
            displayError("Please enter your vehicle model.");
            return false;
        }

        if (!makePattern.test(data.make) || parseInt(data.make) > 2024) {
            displayError("Please enter a valid year until 2024.");
            return false;
        }

        return true;
    }

    function displayError(message) {
        const errorRow = document.getElementById("errorRow");
        const errorMessage = document.getElementById("errorMessage");
        errorMessage.textContent = message;
        errorRow.style.display = "table-row";
    }
});



