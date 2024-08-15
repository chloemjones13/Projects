let timer;
let seconds = 0;
let rep = 1;
let breakRep = 1;
let breakVal = false;
const break1 = 120;
const break2 = 150;
let finshed = false;

const updateTimer = () => {
    var countDown = document.getElementById("myCheckBox").checked;

    if (countDown && !breakVal && ((rep % 2 === 1 && seconds >= 55) || (rep % 2 === 0 && seconds >= 65))) {
        speakOption((rep % 2 === 1 ? 60 : 70) - seconds);
    }
    else if(countDown && break1 && seconds >= 115){
        speakOption(120 - seconds);
    }else if(countDown && break2 && seconds >= 145){
        speakOption(150 - seconds);
    }

    if (breakVal && seconds === break1 && breakRep != 3) {
        breakVal = false;
        seconds = 0;
        breakRep++;
    } else if (breakVal && seconds === break2 && breakRep == 3) {
        breakVal = false;
        seconds = 0;
        breakRep++;
    }else if (!breakVal && rep%2==1 && seconds === 60) {
        breakVal = true;
        rep++;
        seconds = 0;
        document.getElementById('currentRep').innerText = rep;
    } else if(!breakVal && rep%2==0 && seconds === 70){
        breakVal = true;
        rep++;
        seconds = 0;
        document.getElementById('currentRep').innerText = rep;
    }
    else if(rep == 5 && breakVal){
        completeWorkout();
        resetTimer();
        triggerConfetti();
    }

    seconds++;
    document.getElementById('timer').innerText = new Date(seconds * 1000).toISOString().substr(14, 5);
    document.getElementById('breakVal').innerText = breakVal ? "Rest" : "Go!";
};

const speakOption = (number) =>{
    var msg = new SpeechSynthesisUtterance();
    msg.text = number.toString();
    window.speechSynthesis.speak(msg);
};

const startTimer = () => {
    startWorkout();
    if (!timer) {
        timer = setInterval(updateTimer, 1000);
    }
};

const pauseTimer = () => {
    clearInterval(timer);
    timer = null; // Reset timer to allow starting again
};

const resetTimer = () => {

    if (timer) {
        clearInterval(timer);
        timer = null;
    }
    
    seconds = 0;
    rep = 1;
    breakRep = 1;
    breakVal = false;

    document.getElementById('currentRep').innerText = rep;
    document.getElementById('timer').innerText = "00:00";
    document.getElementById('breakVal').innerText = "Go!";
};

function startWorkout() {
    // Call the Flask route to update the count
    fetch('/startS_workout')
    .then(response => {
        if (response.ok) {
            console.log('Shuttle workout started and recorded.');
        }
    })
    .catch(error => console.error('Error:', error));
}

function completeWorkout() {
    // Call the Flask route to update the count
    fetch('/completeS_workout')
    .then(response => {
        if (response.ok) {
            console.log('Shuttle workout completed and recorded.');
        }
    })
    .catch(error => console.error('Error:', error));
}

