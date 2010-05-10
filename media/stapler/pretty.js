/*
 * JavaScript Pretty Date
 * Copyright (c) 2008 John Resig (jquery.com)
 * Licensed under the MIT license.
 */

// Takes an ISO time and returns a string representing how
// long ago the date represents.
function prettyDate(time){
  var cleaned_iso = (time || "").replace(/-/g,"/")
                                .replace(/[TZ]/g," ")
                                .replace(/\.\d+/g,'');
  var date = new Date(cleaned_iso), 
      diff = (((new Date()).getTime() - date.getTime()) / 1000),
      day_diff = Math.floor(diff / 86400);

  if ( diff < 0 )         // der Fall passiert, wenn die Uhrzeit im Parameter VOR 
    return "Unbekannt";   // der aktuellen Client-Uhrzeit liegt. 
  if ( isNaN(day_diff) || day_diff < 0 || day_diff >= 31 )
    return;
      
  return day_diff == 0 && ( diff < 60 && "gerade jetzt" ||
                            diff < 120 && "vor 1 Minute" ||
                            diff < 3600 && "vor " + Math.floor( diff / 60 ) + " Minuten" ||
                            diff < 7200 && "vor 1 Stunde" ||
                            diff < 86400 && "vor " + Math.floor( diff / 3600 ) + " Stunden") ||
                          day_diff == 1 && "Gestern" ||
                          day_diff < 7 && "vor " + day_diff + " Tagen" ||
                          day_diff < 31 && "vor " + Math.ceil( day_diff / 7 ) + " Wochen";
}

// If jQuery is included in the page, adds a jQuery plugin to handle it as well
if ( typeof jQuery != "undefined" )
  jQuery.fn.prettyDate = function(){
    return this.each(function(){
      var date = prettyDate(this.title);
      if ( date )
        jQuery(this).text( date );
    });
  };
