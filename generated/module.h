#ifndef MODULE_H
#define MODULE_H

class AEBSystem {
public:
    AEBSystem();
    void acquireSensorData();
    double calculateTTC();
    bool checkCollisionWarning();
    bool initiateEmergencyBraking();

private:
    double sensorData;
    double ttc;
};

#endif // MODULE_H
