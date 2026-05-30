document.addEventListener("DOMContentLoaded", function () {


    if (window.VANTA && document.querySelector("#anibg")) {
        VANTA.WAVES({
            el: "#anibg",
            mouseControls: true,
            touchControls: true,
            gyroControls: false,
            minHeight: 200,
            minWidth: 200,
            scale: 1,
            scaleMobile: 1,
            color: 0x880020
        });
    }

   
    const locations = {
        "NCR": ["Caloocan","Las Piñas","Makati","Malabon","Mandaluyong","Manila","Marikina","Muntinlupa","Navotas","Parañaque","Pasay","Pasig","Quezon City","San Juan","Taguig","Valenzuela","Pateros"],
        "CAR": ["Abra","Apayao","Benguet","Ifugao","Kalinga","Mountain Province"],
        "Region 1": ["Ilocos Norte","Ilocos Sur","La Union","Pangasinan"],
        "Region 2": ["Batanes","Cagayan","Isabela","Nueva Vizcaya","Quirino"],
        "Region 3": ["Aurora","Bataan","Bulacan","Nueva Ecija","Pampanga","Tarlac","Zambales"],
        "Region 4A": ["Batangas","Cavite","Laguna","Quezon","Rizal"],
        "Region 4B": ["Marinduque","Occidental Mindoro","Oriental Mindoro","Palawan","Romblon"],
        "Region 5": ["Albay","Camarines Norte","Camarines Sur","Catanduanes","Masbate","Sorsogon"],
        "Region 6": ["Aklan","Antique","Capiz","Guimaras","Iloilo","Negros Occidental"],
        "Region 7": ["Bohol","Cebu","Negros Oriental","Siquijor"],
        "Region 8": ["Biliran","Eastern Samar","Leyte","Northern Samar","Samar","Southern Leyte"],
        "Region 9": ["Zamboanga del Norte","Zamboanga del Sur","Zamboanga Sibugay"],
        "Region 10": ["Bukidnon","Camiguin","Lanao del Norte","Misamis Occidental","Misamis Oriental"],
        "Region 11": ["Davao de Oro","Davao del Norte","Davao del Sur","Davao Occidental","Davao Oriental"],
        "Region 12": ["Cotabato","Sarangani","South Cotabato","Sultan Kudarat"],
        "Region 13": ["Agusan del Norte","Agusan del Sur","Dinagat Islands","Surigao del Norte","Surigao del Sur"],
        "BARMM": ["Basilan","Lanao del Sur","Maguindanao del Norte","Maguindanao del Sur","Sulu","Tawi-Tawi"]
    };

    const regionSelect = document.getElementById("region");
    const provinceSelect = document.getElementById("province");

    if (regionSelect && provinceSelect) {

        const selectedRegion = regionSelect.dataset.selected || "";
        const selectedProvince = provinceSelect.dataset.selected || "";

   
        regionSelect.innerHTML = "<option value=''>Select Region</option>";

        Object.keys(locations).forEach(region => {
            const option = document.createElement("option");
            option.value = region;
            option.textContent = region;

            if (region === selectedRegion) {
                option.selected = true;
            }

            regionSelect.appendChild(option);
        });

     
        function loadProvinces(region) {

            provinceSelect.innerHTML = "<option value=''>Select Province</option>";

            if (!locations[region]) {
                provinceSelect.disabled = true;
                return;
            }

            locations[region].forEach(province => {
                const option = document.createElement("option");
                option.value = province;
                option.textContent = province;

                if (province === selectedProvince) {
                    option.selected = true;
                }

                provinceSelect.appendChild(option);
            });

            provinceSelect.disabled = false;
        }

     
        const initialRegion = selectedRegion || Object.keys(locations)[0];

        regionSelect.value = initialRegion;
        loadProvinces(initialRegion);

      
        regionSelect.addEventListener("change", function () {
            loadProvinces(this.value);
        });
    }

    
    if (window.bootstrap) {
        document.querySelectorAll(".toast").forEach(toast => {
            new bootstrap.Toast(toast).show();
        });
    }

});