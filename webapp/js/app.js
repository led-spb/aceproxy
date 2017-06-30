$( function(){
      var channels = {};

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

      $.getJSON( "search/?json", update );
      $.getJSON( "rec/status/", update_rec );

      function set_favorites(list){
         Cookies.set("fav", (list || []).join(";") , {expires: 5*365} );
      }
      function get_favorites(){
         cookie = Cookies.get( "fav" ) || ""
         return cookie.split(";")
      }

      var favorites = get_favorites();

      function update_rec( data ){
         $("#record").empty();

         $.each( data['show']['media'] || {}, function(channel_id, info){
             $("#record").
                append( '<div class="rec_item well well-sm">Rec: '+info['channel']+'<div class="btn btn-xs btn-default pull-right">Stop</div></div>')
                  .find(".btn").click( function(){
                        console.log('Stop rec', channel_id);
                        $.getJSON("record/stop/"+channel_id, update_rec );
                  });
         });
      }

      function create_channel(item){
          /*
          var tile = $('<div class="channel hidden"><div class="item_name">'+item.name+
//                     '<button class="btn btn-default btn-xs pull-right btn-rec" type="button"><span class="glyphicon recicon"></span></button>'+
                     '<button class="btn btn-default btn-xs pull-right btn-rec" type="button">Rec</button>'+
                     '<button class="btn btn-default btn-xs pull-left btn-fav" type="button"><span class="glyphicon favicon"></span></button>'+
                   '</div><a href="play/'+item.id+'"><div class="item_icon" style="background-image:url('+item.logo+')"></div></a></div>');

          tile.find(".btn-rec").click( function(){
              console.log("Start recording", item.id);
              $.getJSON("record/start/"+item.id, update_rec );
          });
          tile.find(".btn-fav").click( function(){
               var idx = favorites.indexOf(item.name);
               if( idx!=-1 ){
                 favorites.splice(idx, 1 );
               }else{
                 favorites.push(item.name);
               } 
               set_favorites(favorites);
               tile.toggleClass("FAVORITES");
               //$(this).parents(".channel").toggleClass("FAVORITES")
          });*/
          var tile = $("#templates .channel").clone();

          tile.find(".channel-name").text( item.name ).attr('href', 'channel/uuid/'+item.id );
          /*
          tile.find(".btn-record").click( function(){
             console.log("Start recording channel "+ item.name);
          });

          tile.find(".channel-logo").css("background-image","url('"+item.logo+"')"); */
          return tile
      }

      function update( data ){
          //set_favorites(favorites);

          var cats = $("#cats");
          var categories = [];
          var holder = $(".channels");

          $.each(data, function(idx, item){
             var element = create_channel(item);//$('<div class="channel hidden"><a href="'+item.uri+'"><div class="item_icon" style="background-image:url('+item.logo+')"></div></a><div class="item_name"><span class="recicon glyphicon"></span>'+item.name+'<span class="favicon glyphicon"></span></div></div>');
             /*
             element.find(".recicon").parent().click( function(){
                $(this).toggleClass('active');
                var channel = channels[item.id];

                 console.log("Start recording "+channel.info.id);
             });*/

             /*
             $.each( item.tags, function(idx, value){
                  element.addClass( value );
                  if( categories.indexOf(value)==-1 ){
                     categories.push( value )
                  }
             } );
             */
             if( favorites.indexOf(item.name) != -1 ) element.addClass( 'FAVORITES' );
             channels[item.id] = { info: item };
             //holder.append( element )
             element.appendTo( holder );
          });
          // $(".channels.channel").remove
          /*
          $.each(categories, function(idx, value ){
              cats.append(' <button class="btn btn-default btn-xs filter-btn" data-filter="'+value+'">'+value+'</button>' );
          })

          var filterByClass = function( filter ){
             $( "#search").val("");
             holder.find( ".channel" ).hide();
             $( filter.join(",") ).show();
          };*/
          var filterByName = function( text ){
             holder.find( ".channel" ).hide();
             cats.find(".active").removeClass("active");

             if(text=="") return;
             $( '.channel:contains("'+text+'")' ).show();
          };

          var oldVal = "";
          $("#search").keyup( function(){ if(oldVal!=this.value){ filterByName(this.value); oldVal=this.value } } );

          // filterByClass( ['.FAVORITES'] );
          /*
          $(".filter-btn").on('click', function(){
               $(this).toggleClass('active').blur();
               var filter=[];
               $(".filter-btn.active").each(
                  function(){ 
                     filter.push( "."+$(this).attr('data-filter') ) 
                  }
               ).promise().done( function(){ filterByClass( filter ) } );
            }
          );
          */
      } 
   } 

);

/*
function export_playlist(){
   playlist = "#EXTM3U url-tvg=\"http://www.teleguide.info/download/new3/jtv.zip\"\n"
   $.each( $(".FAVORITES"), function(i,x){
       var title = $(x).find(".item_name").text(),
           id = $(x).find(".item_id").text();

       playlist = playlist+'#EXTINF:-1 group-title="Public" tvg-name="'+title+'",'+title+"\n"
       playlist = playlist+"http://192.168.168.2:8800/channel/uuid/"+id+"\n"
   });
   console.log(playlist);
}
*/