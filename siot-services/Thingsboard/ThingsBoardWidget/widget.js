self.onInit = function() {      
    self.ctx.$scope.sendCommand = function() {
        // Get the value of the input fields         
        var tachographToConfigure = self.ctx.$scope.tachographToConfigure;         
        var telemetryFrequencyData = self.ctx.$scope.telemetryFrequency;  
        var sensorsSamplingFrequency = self.ctx.$scope.sensorsFrequency;  

        var timeout = self.ctx.settings.requestTimeout; // Get the timeout value from the widget settings         
        var oneWayElseTwoWay = self.ctx.settings.oneWayElseTwoWay ? true : false; // Get the oneWayElseTwoWay value from the widget settings          

        var commandObservable;  // The observable that will be used to send the command to the device       
        var rpcMethod = "modify_frequencies"; // The name of the RPC method to call
        var paramsObject = { "TachographUnit":tachographToConfigure,  // The parameters to pass to the RPC method    
                             "TelemetryFrequency": telemetryFrequencyData, 
                             "SensorsSamplingFrequency": sensorsSamplingFrequency
                           };

        var rpcParams = JSON.stringify(paramsObject); // Convert the parameters to a JSON string
        
        // Call the appropriate RPC method based on the oneWayElseTwoWay value
        if (oneWayElseTwoWay) {             
            commandObservable = self.ctx.controlApi.sendOneWayCommand(rpcMethod, rpcParams, timeout);      
        } else {             
            commandObservable = self.ctx.controlApi.sendTwoWayCommand(rpcMethod, rpcParams, timeout);    
        }         

        // Subscribe to the observable to get the response from the device.
        commandObservable.subscribe(
            // Success callback             
            function (response) {                 
                if (oneWayElseTwoWay) {                     
                    self.ctx.$scope.routeAssignmentResponse = "Command was successfully received by device.<br> No response body because of one way command mode.";                 
                } else {                     
                    self.ctx.$scope.routeAssignmentResponse = "Response from device:<br>";                     
                    self.ctx.$scope.routeAssignmentResponse += JSON.stringify(response, undefined, 2); // Convert the response to a JSON string              
                }                 
                self.ctx.detectChanges();             
            },
            // Error callback             
            function (rejection) {                 
                self.ctx.$scope.routeAssignmentResponse = "Failed to send command to the device:<br>"; 
                self.ctx.$scope.routeAssignmentResponse += "Status: " + rejection.status + "<br>"; 
                self.ctx.$scope.routeAssignmentResponse += "Status text: '" + rejection.statusText + "'"; 
                self.ctx.detectChanges(); 
            } 
        ); 
    } 
} 