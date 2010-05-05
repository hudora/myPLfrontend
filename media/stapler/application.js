
/**
 * jQuery Touch initialisieren.
 */
jQT=$.jQTouch({
  icon: 'foo.png',
  statusBar: 'black'
});

/**
 * program init hook, wird aufgerufen, wenn die Seite komplett
 * geladen ist. Die Methode verbindet hauptsaechlich die Links 
 * mit den entsprechenden Funktionen
 */
$(document).ready(function() {
  $("a#doLogin").click(login);
  $("a#doLogout").click(logout);
  $("a#fetchMovement").click(fetchMovement);
  $("a#cancelMovement").click(cancelMovement);
  $("a#commitMovement").click(function() { return commitOrCancelMovement('commit'); });
  $("a#showHistory").click(showHistory);
  displayCurrentOrClearMovement();
});

/**
 * laedt die letzten 10 Umlagerungen des Benutzers 
 * aus der Datenbank und zeigt sie tabellarisch an.
 */
function showHistory() {
  $('ul#historyList').html("<li>Wird geladen...</li>");
  jQT.goTo('#history','slide'); 
  deactivateLinks();

  $.ajax({
    url: '/stapler/history/',
    dataType: 'json',
    type: 'post',
    error: function() { $('ul#historyList').html("<li>Fehler!</li>"); },
    success: fillHistory
  });
  return false;
};

/**
 * zeigt die vom Server empfangenen letzten 10 Umlagerungen
 * des Benutzers an
 */
function fillHistory(data, status) {
  var historyList=$('ul#historyList');
  historyList.html("");
  if(data['status']!='OK')
    historyList.html("<li>keine gültigen Daten!</li>");
  else {
    var movements=data['data'];
    for(idx in movements) {
      var job=movements[idx],
          createdAt=prettyDate(job['created_at']);
      historyList.append('<li>'+job['from_location']+' -> '+job['to_location']+'<br/>'+
                         '<h1>ArtNr.: '+job['artnr']+', '+job['menge']+' Stück</h1>'+
                         '<h1>'+createdAt+' ('+job['status']+')</h1>'+
                         '</li>');
    }
  }
  return false;
}

/**
 * Startet einen Loginversuch, der spaeter ueber den Callback
 * abgehandelt wird.
 */
function login() {
  $('#loginSubmit').hide();
  $('#loginSpinner').show();
  $.ajax({
    url: '/stapler/login/',
    data: { username: $('input#username').val(),
            password: $('input#password').val() },
    dataType: 'json',
    type: 'post',
    error: loginCallback,
    success: loginCallback});
}

/**
 * Wenn der Login erfolgreich war wird das Formular fuer die
 * Umlagerungen angezeigt, ansonsten gibt's eine Fehlermeldung. 
 * Sollte fuer den Benutzer noch eine aktuelle Umlagerung bestehen
 * wird diese automatisch angezeigt, ansonsten wird das leere 
 * Formular fuer eine neue Umlagerung sichtbar gemacht.
 */
function loginCallback(data, status) {
  if(data['status']=='OK')
    displayCurrentOrClearMovement('flip');
  else
    alert('Benutzername oder Passwort falsch');

  deactivateLinks();
  $('#loginSubmit').show();
  $('#loginSpinner').hide();
}

/**
 * beendet die Benutzer-Session
 */
function logout() {
  $('#movementData').hide();
  $('#movementSpinner').show();
  $.post('/stapler/logout');
  jQT.goBack('#login');
  return false;
}

/**
 * ueberprueft, ob fuer den Benutzer noch eine aktuelle 
 * Umlagerung vorliegt. Dann wird diese automatisch gezogen 
 * und angezeigt, ansonsten wird das leere Movement-Formular
 * dargestellt
 */
function displayCurrentOrClearMovement(transition) {
  $.getJSON('/stapler/is_logged_in', function(data) {
    if(data['login']) {
      data['current_movement'] ? fetchMovement() : clearMovement();
      if(transition)
        jQT.goTo('#movement',transition);
      else
        jQT.goTo('#movement');
    }
  });
}

/**
 * startet den Abruf einer neuen Umlagerung.
 */
function fetchMovement() {
  $('#movementSpinner').show();
  $.ajax({
    url: '/stapler/fetch_movement/',
    dataType: 'json',
    type: 'post',
    error: fetchMovementCallback,
    success: fetchMovementCallback});
  return false;
}

/**
 * Callback zum Anzeigen einer neuen Umlagerung. Wenn der 
 * Aufruf erfolgreich war werden die Daten der Umlagerung 
 * sichtbar gemacht, ansonsten wird das Formluar geloescht
 */
function fetchMovementCallback(data,status) {
  if(data['status']=='open') {
    $('#moveSource').text(  data['from_location']);
    $('#moveDest').text(    data['to_location']);
    $('#moveQuantity').text(data['menge']);
    $('#moveArtnr').text(   data['artnr']);
    $('#moveOid').val(      data['oid']);

    $('#actionsButtons').show();
    $('#movementButtons').hide();
    $('#movementSpinner').hide();
  }
  else if(data['status']=='not_found') {
    clearMovement();
    alert('Es liegt keine Umlagerung vor.');
  }
  else {
    clearMovement();
    alert('Bei der Anforderung ist ein Fehler aufgetreten!');
  }
}

/**
 * convienice method, meldet die aktuelle Umlagerung entweder 
 * erfolgreich zurueck oder storniert sie. Der +what+ Parameter
 * darf dazu entweder 'cancel' oder 'commit' sein. Andere Werte
 * sind nicht zulaessig und fuehren zu 404 beim Server!
 */
function commitOrCancelMovement(what) {
  $('#movementSpinner').show();
  deactivateLinks();

  var oid=$('#moveOid').val(oid);
  $.ajax({
    url: '/stapler/'+what+'_movement/',
    data: {'oid': oid},
    dataType: 'json',
    type: 'post',
    error: commitOrCancelMovementCallback,
    success: commitOrCancelMovementCallback});
  return false;
}

/**
 * Callback fuer die Rueckmeldung/ Stornierung. Wenn eine 
 * Aktion erfolgreich ausgefuehrt worden ist wird automatisch
 */
function commitOrCancelMovementCallback(data,status) {
  if(data['status']!='OK') {
    alert("Die Umlagerung konnte nicht bearbeitet werden!");
    $('#movementSpinner').hide();
  }
  else {
    clearMovement();
    alert("Die Umlagerung wurde bearbeitet.");
  }
}

/**
 * bricht nach einer Sicherheitsabfrage die aktuelle Umlagerung ab
 */
function cancelMovement() {
  deactivateLinks();
  if(confirm('Umlagerung wirklich stornieren?'))
    commitOrCancelMovement('cancel');
}

/**
 * sorgt dafuer, das alle Buttons/ Links nicht mehr blau hinterlegt 
 * dargestellt werden, nachdem sie angeklickt worden sind.
 */
function deactivateLinks() {
  var targets=['showHistory', 'fetchMovement','commitMovement','cancelMovement','doLogin','doLogout']
  for(idx in targets)
    $('a#'+targets[idx]).removeClass('active');
}

/**
 * loescht die aktuell angezeigte Umlagerung aus dem Formular.
 */
function clearMovement() {
  $('#moveSource').text('');
  $('#moveDest').text('');
  $('#moveQuantity').text('');
  $('#moveArtnr').text('');
  $('#moveOid').val('');

  $('#username').val('');
  $('#password').val('');

  $('#actionsButtons').hide();
  $('#movementButtons').show();
  $('#movementSpinner').hide();
  deactivateLinks();
}
