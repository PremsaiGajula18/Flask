document
    .getElementById("studentForm")
    .addEventListener("submit", function(event) {

        // Stop normal form submission
        event.preventDefault();


        // Get input values

        let name =
            document.getElementById("name").value;

        let email =
            document.getElementById("email").value;

        let age =
            document.getElementById("age").value;


        // Validation

        if (name.trim() === "") {

            alert("Please enter name");
            return;

        }


        if (email.trim() === "") {

            alert("Please enter email");
            return;

        }


        if (age.trim() === "") {

            alert("Please enter age");
            return;

        }


        // Send data to Flask

        fetch("/add", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                name: name,
                email: email,
                age: age

            })

        })


        // Receive Flask response

        .then(response => response.json())


        .then(data => {

            document
                .getElementById("message")
                .innerText = data.message;


            if (data.success) {

                // Clear inputs

                document
                    .getElementById("studentForm")
                    .reset();


                // Reload page

                setTimeout(function() {

                    location.reload();

                }, 500);

            }

        })


        .catch(error => {

            console.error("Error:", error);

        });

    });