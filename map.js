  var map, infoWindow, heatmap, tracking;

  function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
      center: {lat: 42.728351, lng: -84.481976},
      zoom: 6
    });
    infoWindow = new google.maps.InfoWindow;
    tracking = true;
    heatmap = new google.maps.visualization.HeatmapLayer({
        data: getPoints(),
          map: map
        });

    // Try HTML5 geolocation.
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(position) {
        var pos = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };

        map.setCenter(pos);
      }, function() {
        handleLocationError(true, infoWindow, map.getCenter());
      });
    } else {
      // Browser doesn't support Geolocation
      handleLocationError(false, infoWindow, map.getCenter());
    }
  }

  function selectRoad() {
      heatmap = new google.maps.visualization.HeatmapLayer({
        data: getRoadPoints(),
          map: map
        });
  }

  function selectAccidents() {
      heatmap = new google.maps.visualization.HeatmapLayer({
        data: getAccidentPoints(),
          map: map
        });
  }

  function handleLocationError(browserHasGeolocation, infoWindow, pos) {
    infoWindow.setPosition(pos);
    infoWindow.setContent(browserHasGeolocation ?
                          'Error: The Geolocation service failed.' :
                          'Error: Your browser doesn\'t support geolocation.');
    infoWindow.open(map);
  }

  function getRoadPoints() {
      return {{ all_road_points }}
  }

  function getAccidentPoints() {
      return {{ all_accident_points }}
  }

  function toggleTracking() {
      if (tracking) {
          tracking = false;
      } else {
          tracking = true;
      }
  }

  setInterval(function() {
    if (tracking) {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
          var pos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };

          map.setCenter(pos);
        }, function () {
          handleLocationError(true, infoWindow, map.getCenter());
        });
      } else {
        // Browser doesn't support Geolocation
        handleLocationError(false, infoWindow, map.getCenter());
      }
    }
  }, 3000)
