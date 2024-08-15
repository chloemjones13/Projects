from flask import Flask, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = '0827'  # Set a secret key for session management

@app.route('/')
def index():
    # Render the home page
    return render_template('index.html')

@app.route('/manu')
def manu():
    # Render the ManU timer page
    return render_template('manu.html')

@app.route('/shuttles')
def shuttles():
    # Render the Shuttles timer page
    return render_template('shuttles.html')

@app.route('/acomplishments')
def acomplishments():
    # Retrieve workout statistics from session
    shuttle_started = session.get('shuttle_started', 0)
    manU_started = session.get('manU_started', 0)
    shuttle_completed = session.get('shuttle_completed', 0)
    manU_completed = session.get('manU_completed', 0)
    
    # Render the accomplishments page with statistics
    return render_template('acomplishments.html', shuttleStarted=shuttle_started, 
                           manUStarted=manU_started, shuttlesCompleted=shuttle_completed, 
                           manUCompleted=manU_completed)

@app.route('/startS_workout')
def startedS_workout():
    # Increment the count of started Shuttle workouts
    session['shuttle_started'] = session.get('shuttle_started', 0) + 1
    return redirect(url_for('shuttles'))  # Redirect to the Shuttles page

@app.route('/startM_workout')
def startedM_workout():
    # Increment the count of started ManU workouts
    session['manU_started'] = session.get('manU_started', 0) + 1
    return redirect(url_for('manu'))  # Redirect to the ManU page

@app.route('/completeS_workout')
def completedS_workout():
    # Increment the count of completed Shuttle workouts
    session['shuttle_completed'] = session.get('shuttle_completed', 0) + 1
    return redirect(url_for('shuttles'))  # Redirect to the Shuttles page

@app.route('/completeM_workout')
def completedM_workout():
    # Increment the count of completed ManU workouts
    session['manU_completed'] = session.get('manU_completed', 0) + 1
    return redirect(url_for('manu'))  # Redirect to the ManU page

if __name__ == "__main__":
    app.run(debug=True)  # Run the app in debug mode
