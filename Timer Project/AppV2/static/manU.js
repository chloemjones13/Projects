// Declare variables to control the timer and workout logic
let timer; // Will store the interval ID for the timer
let seconds = 0; // Keeps track of the number of seconds elapsed
let rep = 1; // Tracks the current repetition number
let breakVal = false; // Boolean to check if it's break time or workout time
let finshed = false; // Unused variable, possibly a typo (finshed -> finished?)
let breakTime = 35; // Duration of break time in seconds
let runTime = 25; // Duration of workout time in seconds

// Function to update the timer and control the flow of the workout
const updateTimer = () => {
    // Get the status of the countdown checkbox
    var countDown = document.getElementById("myCheckBox").checked;

    // Calculate remaining time based on whether it's break or workout time
    let timeRemaining = (breakVal ? breakTime : runTime) - seconds;

    // If countdown is active and time is less than or equal to 5 seconds, announce the remaining time
    if (countDown && timeRemaining <= 5 && timeRemaining > 0) {
        speakOption(timeRemaining);
    }

    // Handle the transition from break to workout and increment the repetition count
    if (breakVal && seconds === breakTime) {
        breakVal = false; // End break
        seconds = 0; // Reset seconds for next phase
        rep++; // Increment the repetition count
        document.getElementById('currentRep').innerText = rep; // Update displayed repetition count

    // Handle the transition from workout to break time, if under 11 reps
    } else if (!breakVal && seconds === runTime && rep <= 10) {
        breakVal = true; // Start break
        seconds = 0; // Reset seconds for the break time

    // After 11th rep, gradually increase break time and decrease workout time
    } else if (!breakVal && seconds === runTime && rep >= 11) {
        breakVal = true; // Start break
        seconds = 0; // Reset seconds
        breakTime++; // Increase break time by 1 second
        runTime--; // Decrease workout time by 1 second

    // If the rep count reaches 21, complete and reset the workout
    } else if (rep == 21) {
        completeWorkout(); // Mark workout as complete
        resetTimer(); // Reset the timer and variables
    }

    // Increment the seconds counter and update the timer display
    seconds++;
    document.getElementById('timer').innerText = new Date(seconds * 1000).toISOString().substr(14, 5);
    // Update the display to indicate whether it's rest time or workout time
    document.getElementById('breakVal').innerText = breakVal ? "Rest" : "Go!";
};

// Function to start the timer and the workout
const startTimer = () => {
    document.getElementById('currentRep').innerText = rep; // Display the current rep number
    if (!timer) {
        timer = setInterval(updateTimer, 1000); // Start the timer to update every second
    }
    startWorkout(); // Start the workout and record it via Flask
};

// Function to pause the timer
const pauseTimer = () => {
    clearInterval(timer); // Stop the interval, pausing the timer
    timer = null; // Reset timer variable to allow restart
};

// Function to announce the remaining seconds using speech synthesis
const speakOption = (number) => {
    var msg = new SpeechSynthesisUtterance(); // Create a new speech message
    msg.text = number.toString(); // Set the text to the number
    window.speechSynthesis.speak(msg); // Speak the message
};

// Function to reset the timer and all related variables
const resetTimer = () => {
    if (timer) {
        clearInterval(timer); // Stop the timer if it's running
        timer = null; // Reset the timer variable
    }

    // Reset all variables to their initial states
    seconds = 0;
    rep = 1;
    breakVal = false;

    // Update the UI to reflect the reset state
    document.getElementById('currentRep').innerText = rep;
    document.getElementById('timer').innerText = "00:00";
    document.getElementById('breakVal').innerText = "Go!";
};

// Function to start the workout and log it to the server using Flask
function startWorkout() {
    fetch('/startM_workout')
    .then(response => {
        if (response.ok) {
            console.log('ManU workout started and recorded.');
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to complete the workout and log it to the server using Flask
function completeWorkout() {
    fetch('/completeM_workout')
    .then(response => {
        if (response.ok) {
            console.log('ManU workout completed and recorded.');
        }
    })
    .catch(error => console.error('Error:', error));
}
