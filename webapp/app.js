$( function(){
      window.channels = {};
      var holder = $(".channels");

      $.expr[":"].contains = $.expr.createPseudo(function(arg) {
          return function( elem ) {
              try{
                 var expr = new RegExp(arg,  "i" );
                 return $(elem).text().search( expr ) >= 0;
              }catch(err){
                 return false;
              }
          };
      });

      // Initial requests
      $.when(
         $.getJSON( "search?json"),  $.getJSON( "record/status" )
      ).then( function(res1, res2){
         var channels = res1[0];
         var records = res2[0];
         update( channels );
         update_rec( records );
         setInterval( function(){  $.getJSON( "record/status", update_rec ); }, 30000 );
      });

      function update_rec( data ){
         $(".status .disk-free").text( filesize(data.disk_avail) )
         $(".status .disk-free-pct").text( Math.ceil((data.disk_total-data.disk_avail)/data.disk_total*10000)/100+"%" )

         $(".channel.record").removeClass("record")
         $.each( data['show']['media'] || {}, function(channel_id, info){
             if( channels[channel_id] ){
                 var element = channels[channel_id].element;

                 element.addClass('record');
                 element.show();
                 element.find(".record-duration").text( moment().from( moment(info.started), true ) );
                 element.find(".record-size").text( filesize(info.recorded) );
             }
         });

         $(".channel .btn-record-start").show();
         $(".channel .btn-record-stop").hide();

         $(".channel.record .btn-record-start").hide();
         $(".channel.record .btn-record-stop").show();
      }

      function on_record_start(){
         channel_id = $(this).data('channel-id');
         var element = channels[channel_id]
         console.log('Start record '+channel_id);
         $.getJSON( "record/start/"+channel_id, update_rec );
      }
      function on_record_stop(){
         channel_id = $(this).data('channel-id');
         var element  = channels[channel_id].element;
         element.removeClass('record');
         console.log('Stop record '+channel_id);
         $.getJSON( "record/stop/"+channel_id, update_rec );
      }

      function create_channel(item){
          var tile = $("#templates .channel").clone();
          tile.find(".channel-name").text( item.name ).attr('href', 'channel/uuid/'+item.id );

          tile.find(".btn-record-start").data('channel-id', item.id ).click( on_record_start );
          tile.find(".btn-record-stop").data('channel-id', item.id ).click( on_record_stop);
          return tile
      }


      function update( data ){
          $.each(data, function(idx, item){
             var element = create_channel(item);
             channels[item.id] = {
                info:    item, 
                element: element 
             };
             element.appendTo( holder );
          });
      }

      var oldVal = "";
      $("#search").keyup( function(){ 
           if( oldVal!=this.value){ 
               var text = this.value;
               holder.find( ".channel" ).hide();
               $( '.channel.record').show();
               if( text == "") return;
               $( '.channel:contains("'+text+'")' ).show()
               oldVal = text;
           }
      });
   }
);