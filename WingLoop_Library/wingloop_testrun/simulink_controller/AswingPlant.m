classdef AswingPlant < matlab.System
    % ASWINGPLANT MATLAB System Block for WingLoop TCP Bridge
    %
    % Double click on this block in Simulink to configure the number of states!
    
    properties (Nontunable)
        ServerHost        = 'localhost' 
        ServerPort        = 5005
        NumModalStates    = 91   % Modify this value from the Simulink Mask if there is A ROM!
        NumPhysicalStates = 1888 % Modify this value from the Simulink Mask!
    end

    properties (Access = private)
        tcp_client
        step_count = 0;
    end

    methods (Access = protected)
        function setupImpl(obj)
            fprintf('[AswingPlant] Starting connection to %s:%d...\n', obj.ServerHost, obj.ServerPort);
            
            connected = false;
            retries = 0;
            
            while ~connected && retries < 10
                try
                    obj.tcp_client = tcpclient(obj.ServerHost, obj.ServerPort, 'Timeout', 30);
                    connected = true;
                catch
                    fprintf('[AswingPlant] Waiting for Python server to start... (attempt %d/10)\n', retries+1);
                    pause(1);
                    retries = retries + 1;
                end
            end
            
            if ~connected
                error('Timeout! Unable to connect to Python. Make sure the background script has started correctly.');
            end
            
            obj.step_count = 0;
            fprintf('[AswingPlant] Successfully connected to the Bridge!\n');
        end

        function [z_out, y_phys] = stepImpl(obj, u_commands)
            % 1. Send commands to Python
            msg = jsonencode(struct('cmd','step','u',u_commands(:)'));
            mbytes = uint8(msg); mlen = length(mbytes);
            hdr = uint8([bitshift(mlen,-24), bitand(bitshift(mlen,-16), 255), ...
                         bitand(bitshift(mlen,-8), 255), bitand(mlen, 255)]);
            write(obj.tcp_client, [hdr, mbytes]);

            % 2. Receive states from Python
            rh = read(obj.tcp_client, 4, 'uint8');
            rlen = uint32(rh(1))*16777216 + uint32(rh(2))*65536 + uint32(rh(3))*256 + uint32(rh(4));
            raw_data = read(obj.tcp_client, double(rlen), 'uint8');
            data = jsondecode(char(raw_data));

            z_raw = data.z;
            y_raw = data.y;

            y_phys = zeros(obj.NumPhysicalStates, 1);
            n_y = min(length(y_raw), obj.NumPhysicalStates);
            y_phys(1:n_y) = y_raw(1:n_y);

            z_out = zeros(obj.NumModalStates, 1);
            n_z = min(length(z_raw), obj.NumModalStates);
            z_out(1:n_z) = z_raw(1:n_z);

            % --- RADAR ---
            obj.step_count = obj.step_count + 1;
            if mod(obj.step_count, 50) == 0
                fprintf('[MATLAB Radar] Step %d | Max Y Value: %.6f\n', obj.step_count, max(abs(y_raw)));
            end
        end

        function releaseImpl(obj)
            if ~isempty(obj.tcp_client)
                try
                    msg = uint8(jsonencode(struct('cmd','close')));
                    mlen = length(msg);
                    hdr = uint8([bitshift(mlen,-24), bitand(bitshift(mlen,-16),255), bitand(bitshift(mlen,-8),255), bitand(mlen,255)]);
                    write(obj.tcp_client, [hdr, msg]);
                catch
                end
                delete(obj.tcp_client); obj.tcp_client = [];
            end
            fprintf('[AswingPlant] Disconnected.\n');
        end

        function [s1,s2] = getOutputSizeImpl(obj)
            s1 = [obj.NumModalStates 1];
            s2 = [obj.NumPhysicalStates 1];
        end
        function [d1,d2] = getOutputDataTypeImpl(~)
            d1 = 'double'; d2 = 'double';
        end
        function [c1,c2] = isOutputComplexImpl(~)
            c1 = false; c2 = false;
        end
        function [f1,f2] = isOutputFixedSizeImpl(~)
            f1 = true; f2 = true;
        end
    end
end