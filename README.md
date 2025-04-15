# graphite-image-ticket-to-calendar
Ticket Image to calendar entry in google calendar

Instructions how to use it:

1. Downloading Dependencies:

   1. Make sure you have Poetry installed
   2. The run the following command in your terminal: ```poetry install```

2. Google Cloud Setup:

   1. In your Google Cloud Console, choose/create a project where you would like to work on
   2. Enable the Google Calendar API by searching in the search bar
   3. Create a new service acccount, IAM & Admin > Service Accounts
   4. Now click on your newly created service account → "Keys" tab → "Add Key" → "Create new key" → choose JSON → click Create.
   5. Download the .json key file for the created service account

3. Calendar Permission:

   1. Open Google Calendar
   2. Click on settings and nn the left under Settings for my calendars, select the calendar you want to use.
   3. Find "Share with specific people" and click "Add people"
   4. Paste your service account email you created (it should end in gserviceaccount.com).
   5. Set permissions to "Make changes" to events and click Send, this will allow the agent to make changes to your calendar

4. Adding the credentials file:

   1. Create ```secrets``` folder in your directory and place your key renamed to ```service-account.json``` in there.

5. Configuring the Environment Variables:

   1. Create a ```.env``` file in the project root.
   2. Define the following: ```GOOGLE_CALENDAR_ID``` and ```OPENAI_KEY```
        GOOGLE_CALENDAR_ID - The email address of the calendar where events should appear
        OPENAI_KEY - Your OpenAI key

6. Running the assisstant:

   1. Build the Docker image using ```docker build -t image-event-agent . ```
   2. Run the container using Docker Compose ```docker compose up```
