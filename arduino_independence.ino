unsigned long exp_start;
unsigned long internal_time;
unsigned long incident_time;
unsigned long dispense_time;
int counter;
int x;
bool r_t_s; //Signal ready to start
bool l_lever_out = false; //When true, measure lever voltage
bool r_lever_out = false;
bool dispense_on = false;
int no_single_ir = 0; //Sometimes IR measurements fluctuate to where there will randomly be a >10 value surrounded by zeros, so we want to eliminate these
int no_single_ir_in = 0; //But if the IR sensor is good, i.e. doesn't throw random large values out, we don't need this scheme and can get better temporal resolution
//Sending every timestamp for a given state just overwhelms 
//the buffer that everything is written to, so we are going to only
//report when states change e.g. when the ir beam is broken and when it is unbroken
bool ir_broken = false;
bool lever_pressed = false;

//Lever and dispenser pins and stuff
int left_lever_control = 12;
int left_lever_report = A5;
int left_led = 2;
int sensorValue;
int right_lever_control = 13;
int right_lever_report = A4;
int right_led = 3;

int dispense_control = 11;

//IR detector pins and stuff
int ir_source = 9;
int detect_power = 8;
int detect_signal = A3;
int irValue = 0;

float last_loop;

void setup() {
  
  //Lever and dispenser pins and stuff
  pinMode(left_lever_control, OUTPUT);
  pinMode(left_lever_report, INPUT);
  pinMode(left_led, OUTPUT);

  pinMode(right_lever_control, OUTPUT);
  pinMode(right_lever_report, INPUT);
  pinMode(right_led, OUTPUT);

  pinMode(dispense_control, OUTPUT);
  //IR detector pins and stuff
  pinMode(ir_source, OUTPUT);
  pinMode(detect_power, OUTPUT);
  pinMode(detect_signal, INPUT);
  digitalWrite(ir_source, HIGH);
  digitalWrite(detect_power, HIGH);
  
  Serial.begin(9600);
  r_t_s = false;
  counter = 0;
  //Serial.println(counter);
  last_loop = millis();
}

void loop() {
  float loop_ms = millis();
  if ((loop_ms - last_loop) < 33) {
    return;
  }
  last_loop = loop_ms;    
  //This routine announces the arduino's readiness and traps us until the final confirm signal is given
  if (r_t_s == false) {
    startup_routine();
  }

  x = Serial.read();
  
  //Take care of any incoming instructions
  relay_controls();

  //Measure IR, maybe measure lever
  measure_ir();
  if (l_lever_out or r_lever_out) {
    measure_lever();
  }

  // Measure how many rounds are completed per 1 second
  incident_time = millis();
  if (incident_time - internal_time >= 1000) {
    Serial.print("loop ");
    Serial.println(counter);
    counter = 0;
    internal_time = millis();
  }
  counter += 1;
  //End measuring routine

  endup_routine();
}

void startup_routine() {
  Serial.println("ready"); //Let the computer know we're ready for serial transmission
  while (r_t_s == false) {
    x = Serial.read();  
    if (x == 'g') { // Go signal, all time is relative to this moment
      exp_start = millis();
      internal_time = exp_start; //Using this to time sampling rate, needs to be reset every measurement interval
      r_t_s = true;
      Serial.println("start");
      }
  }
}

void endup_routine() {
  if (x == 's') {
    Serial.println("end");
    while (true) {
      
    }
  }
}

void relay_controls() {
  if (x == 'l') {
    digitalWrite(left_lever_control, HIGH);
    digitalWrite(left_led, HIGH);
    l_lever_out = true;
  }
  else if (x == 'r') {
    digitalWrite(right_lever_control, HIGH);
    digitalWrite(right_led, HIGH);
    r_lever_out = true;
  }
  else if (x == 'd') {
    digitalWrite(dispense_control, HIGH);
    dispense_time = millis();
    dispense_on = true; //Need to turn this off after 5ms
    //Serial.println("we on");
  }
  else if (x == 'k') {
    digitalWrite(left_lever_control, LOW);
    digitalWrite(left_led, LOW);
    digitalWrite(right_lever_control, LOW);
    digitalWrite(right_led, LOW);    
    l_lever_out = false;
    r_lever_out = false;
    if (lever_pressed) { // If the lever is still depressed while being retracted, we consider this moment to be the switch to 'off'
      Serial.print("lever_off ");
      send_report();
      lever_pressed = false;    
    }
  }
  //Don't want to block while we wait 5ms between food dispenser on/off signal
  //so when we dispense, we keep checking back until 5ms passes
  if (dispense_on) {
    if ((millis() - dispense_time) > 5) {
      digitalWrite(dispense_control, LOW);
      dispense_on = false;
      //Serial.println("we off");
    }
  }
}

void measure_ir() {
  irValue = analogRead(detect_signal);
  //Serial.println(irValue);
  if ((irValue < 10) and (ir_broken == false)) {
    if (no_single_ir_in > 2){
      Serial.print("nose_in ");
      send_report();
      ir_broken = true;
    }
    else {
      no_single_ir_in += 1;
    }
  }
  if (irValue < 10) {
    no_single_ir = 0;
  }
  if ((irValue > 10) and (ir_broken == true)) {
    if (no_single_ir > 2) {
      Serial.print("nose_out ");
      send_report();
      no_single_ir = 0;
      ir_broken = false;  
    }
    else {
      no_single_ir += 1;
    }
  }
  if (irValue > 10) {
    no_single_ir_in = 0;
  }
}


void measure_lever() {
  
  if (l_lever_out) {
    sensorValue = analogRead(left_lever_report);
  }
  else if (r_lever_out) {
    sensorValue = analogRead(right_lever_report);
  }
  
  float voltage = sensorValue * (5.0 / 1023.0);
  if ((voltage < 0.5) and (lever_pressed == false)) {
    Serial.print("lever_on ");
    send_report();
    lever_pressed = true;
  }
  else if ((voltage > 0.5) and (lever_pressed == true)) {
    Serial.print("lever_off ");
    send_report();
    lever_pressed = false;    
  }
}

//Gives time since start of experiment in Min:Sec:Millis
void send_report() {
  unsigned long initial_mils = millis() - exp_start;
  int report_mils = initial_mils % 1000; //What remains after converting to seconds
  int initial_sec = initial_mils / 1000; //Seconds without minutes removed
  int report_min = initial_sec / 60; //Removing minutes
  int report_sec = initial_sec % 60; //What remains after converting to minutes
  char buf[11];
  sprintf(buf,"%02d:%02d:%03d",report_min,report_sec,report_mils);
  Serial.println(buf);
}
