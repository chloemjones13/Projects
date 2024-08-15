// Declare the timer variable to store the interval ID for the timer
let timer;

// Initialize the seconds variable to keep track of the elapsed time
let seconds = 0;

// Function to update the timer display every second
const updateTimer = () => {
    // Increment the seconds counter by 1
    seconds++;

    // Update the HTML element with the id 'timer' to show the elapsed time in mm:ss format
    document.getElementById('timer').innerText = new Date(seconds * 1000).toISOString().substr(14, 5);
}

// Function to start the timer
const startTimer = () => {
    // Log a message to the console when the timer is started
    console.log("clicked");

    // Check if the timer is not already running
    if (!timer) {
        // Start the timer and call the updateTimer function every 1000 milliseconds (1 second)
        timer = setInterval(updateTimer, 1000);
    }
}

// Function to pause the timer
const pauseTimer = () => {
    // Stop the timer by clearing the interval
    clearInterval(timer);

    // Reset the timer variable to null, allowing the timer to be restarted later
    timer = null;
}
